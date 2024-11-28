from typing import Dict, Any, List, Optional
import os
import yaml
import json
from pathlib import Path
from .base_agent import BaseAgent

class DeveloperAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config = self._load_config()
        self.tree_focus = self.config.get("tree_focus", {})
        self.allowed_actions = self.config.get("agents", {}).get("developer", {}).get("allowed_actions", [])
        self.domain_rules = self.config.get("agents", {}).get("developer", {}).get("domain_rules", {})

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            return {}
        
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action")
        if action not in self.allowed_actions:
            return {"error": f"Action not allowed: {action}"}

        if action == "create_component":
            return await self._create_component(input_data["component"])
        elif action == "update_component":
            return await self._update_component(input_data["component"])
        elif action == "implement_feature":
            return await self._implement_feature(input_data["feature"])
        elif action == "fix_issue":
            return await self._fix_issue(input_data["issue"])
        return {"error": "Unknown action"}

    async def _create_component(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new component following domain-specific rules."""
        domain = self._get_component_domain(component)
        if not domain:
            return {
                "status": "error",
                "error": "Component domain not recognized",
                "details": "Component must belong to a defined domain in tree_focus"
            }

        # Check naming convention
        if not self._validate_naming_convention(component["name"], domain):
            return {
                "status": "error",
                "error": "Invalid naming convention",
                "details": f"Component name must follow {domain} naming convention"
            }

        # Apply domain-specific rules
        component = self._apply_domain_rules(component, domain)
        
        # Create component files
        created_files = []
        for file_spec in component.get("files", []):
            file_path = file_spec.get("path")
            if not file_path:
                continue

            # Check if path follows domain rules
            if not any(file_path.startswith(dir) for dir in self.tree_focus[domain]["directories"]):
                return {
                    "status": "error",
                    "error": "Invalid file path",
                    "details": f"File must be in one of {self.tree_focus[domain]['directories']}"
                }

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Create file with content
            try:
                with open(file_path, "w") as f:
                    f.write(file_spec.get("content", ""))
                created_files.append(file_path)
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to create file {file_path}",
                    "details": str(e)
                }

        # Create tests if required
        if self.domain_rules.get(domain, {}).get("require_tests", True):
            for file_path in created_files:
                test_path = self._get_test_path(file_path)
                if test_path:
                    try:
                        with open(test_path, "w") as f:
                            f.write(self._generate_test_content(file_path))
                        created_files.append(test_path)
                    except Exception as e:
                        return {
                            "status": "error",
                            "error": f"Failed to create test file {test_path}",
                            "details": str(e)
                        }

        return {
            "status": "success",
            "files": created_files,
            "domain": domain
        }

    def _get_component_domain(self, component: Dict[str, Any]) -> Optional[str]:
        """Get the domain for a component."""
        # First check if domain is explicitly specified
        if "domain" in component:
            domain = component["domain"]
            if domain in self.tree_focus:
                return domain

        # If not found or invalid, try to infer from file paths
        for file_spec in component.get("files", []):
            file_path = file_spec.get("path", "")
            for domain, rules in self.tree_focus.items():
                if any(file_path.startswith(dir) for dir in rules["directories"]):
                    return domain

        return None

    def _apply_domain_rules(self, component: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Apply domain-specific rules to component structure."""
        rules = self.domain_rules.get(domain, {})
        
        # Apply naming conventions
        if "naming_convention" in rules:
            component["name"] = self._apply_naming_convention(
                component["name"],
                rules["naming_convention"]
            )

        # Apply file structure rules
        if "file_structure" in rules:
            component["files"] = self._apply_file_structure(
                component.get("files", []),
                rules["file_structure"]
            )

        # Apply code style rules
        if "code_style" in rules:
            component = self._apply_code_style(component, rules["code_style"])

        return component

    def _apply_naming_convention(self, name: str, convention: str) -> str:
        """Apply naming convention to component name."""
        if convention == "PascalCase":
            return "".join(word.capitalize() for word in name.split("_"))
        elif convention == "camelCase":
            words = name.split("_")
            return words[0] + "".join(word.capitalize() for word in words[1:])
        elif convention == "kebab-case":
            return name.replace("_", "-").lower()
        return name

    def _apply_file_structure(self, files: List[Dict[str, Any]], structure_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply file structure rules to component files."""
        required_files = structure_rules.get("required_files", [])
        
        # Ensure all required files exist
        existing_files = {f.get("path", "").split("/")[-1] for f in files}
        for required in required_files:
            if required not in existing_files:
                files.append({
                    "path": f"{required}",
                    "content": self._get_template_content(required)
                })

        return files

    def _apply_code_style(self, component: Dict[str, Any], style_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Apply code style rules to component."""
        for file in component.get("files", []):
            if file.get("path", "").endswith((".ts", ".tsx")):
                # Apply TypeScript/React specific rules
                file["content"] = self._apply_ts_rules(file["content"], style_rules)
            elif file.get("path", "").endswith(".py"):
                # Apply Python specific rules
                file["content"] = self._apply_python_rules(file["content"], style_rules)

        return component

    def _apply_ts_rules(self, content: str, rules: Dict[str, Any]) -> str:
        """Apply TypeScript code style rules."""
        if rules.get("use_typescript", True):
            # Add type annotations
            content = content.replace("function", "function:")
            content = content.replace("const", "const:")

        if rules.get("use_strict", True):
            content = "'use strict';\n" + content

        return content

    def _apply_python_rules(self, content: str, rules: Dict[str, Any]) -> str:
        """Apply Python code style rules."""
        if rules.get("type_hints", True):
            # Add type hints
            content = content.replace("def ", "def -> None:")

        if rules.get("docstrings", True):
            # Add docstring template
            content = '"""\nModule docstring.\n"""\n' + content

        return content

    async def _create_test_files(self, component: Dict[str, Any], domain: str) -> List[str]:
        """Create test files for component."""
        test_files = []
        
        for file in component.get("files", []):
            file_path = file.get("path")
            if not file_path:
                continue

            test_path = self._get_test_file_path(file_path)
            if not test_path:
                continue

            # Create test file
            os.makedirs(os.path.dirname(test_path), exist_ok=True)
            with open(test_path, "w") as f:
                f.write(self._generate_test_content(file, domain))
            test_files.append(test_path)

        return test_files

    def _get_test_file_path(self, file_path: str) -> str:
        """Get the test file path for a source file."""
        path = Path(file_path)
        if path.suffix in [".ts", ".tsx"]:
            return str(path.parent / f"{path.stem}.test{path.suffix}")
        elif path.suffix == ".py":
            return str(path.parent / f"test_{path.stem}{path.suffix}")
        return None

    def _generate_test_content(self, file: Dict[str, Any], domain: str) -> str:
        """Generate test content based on file type and domain."""
        if file["path"].endswith((".ts", ".tsx")):
            return self._generate_ts_test(file, domain)
        elif file["path"].endswith(".py"):
            return self._generate_python_test(file, domain)
        return ""

    def _generate_ts_test(self, file: Dict[str, Any], domain: str) -> str:
        """Generate TypeScript test content."""
        component_name = Path(file["path"]).stem
        
        return f"""import {{ render, screen }} from '@testing-library/react'
import {{ {component_name} }} from './{component_name}'

describe('{component_name}', () => {{
    it('renders correctly', () => {{
        render(<{component_name} />)
        // Add assertions here
    }})
}})
"""

    def _generate_python_test(self, file: Dict[str, Any], domain: str) -> str:
        """Generate Python test content."""
        module_name = Path(file["path"]).stem
        
        return f"""import unittest
from {module_name} import *

class Test{module_name.capitalize()}(unittest.TestCase):
    def setUp(self):
        pass

    def test_basic_functionality(self):
        # Add test cases here
        pass

if __name__ == '__main__':
    unittest.main()
"""

    async def _update_component(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing component."""
        if not os.path.exists(component.get("path", "")):
            return {"error": "Component does not exist"}

        domain = self._get_component_domain(component)
        if not domain:
            return {"error": "Component domain not recognized"}

        # Apply updates
        updated_files = []
        for file_spec in component.get("files", []):
            file_path = file_spec.get("path")
            if not file_path or not os.path.exists(file_path):
                continue

            try:
                # Update file content
                with open(file_path, "w") as f:
                    f.write(file_spec.get("content", ""))
                updated_files.append(file_path)

                # Update corresponding test file if it exists
                test_path = self._get_test_file_path(file_path)
                if test_path and os.path.exists(test_path):
                    with open(test_path, "w") as f:
                        f.write(self._generate_test_content(file_spec, domain))
                    updated_files.append(test_path)

            except Exception as e:
                return {"error": f"Failed to update file {file_path}", "details": str(e)}

        return {
            "status": "updated",
            "files": updated_files,
            "domain": domain
        }

    async def _implement_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """Implement a new feature across multiple components."""
        domain = feature.get("domain")
        if not domain or domain not in self.tree_focus:
            return {"error": "Invalid feature domain"}

        # Create new components
        created_components = []
        for component in feature.get("components", []):
            result = await self._create_component(component)
            if "error" in result:
                return result
            created_components.extend(result.get("files", []))

        # Update existing components
        updated_components = []
        for component in feature.get("updates", []):
            result = await self._update_component(component)
            if "error" in result:
                return result
            updated_components.extend(result.get("files", []))

        return {
            "status": "implemented",
            "created": created_components,
            "updated": updated_components,
            "domain": domain
        }

    async def _fix_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Fix an issue in the codebase."""
        files = []
        
        # Apply fixes to files
        for file_spec in issue.get("files", []):
            file_path = file_spec.get("path")
            if not file_path:
                continue

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Create or update file with content
            try:
                with open(file_path, "w") as f:
                    f.write(file_spec.get("content", ""))
                files.append(file_path)
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to update file {file_path}",
                    "details": str(e)
                }

        # Update tests if required
        if issue.get("update_tests", False):
            for file_path in files:
                test_path = self._get_test_path(file_path)
                if test_path:
                    try:
                        with open(test_path, "w") as f:
                            f.write(self._generate_test_content(file_path))
                        files.append(test_path)
                    except Exception as e:
                        return {
                            "status": "error",
                            "error": f"Failed to update test file {test_path}",
                            "details": str(e)
                        }

        return {
            "status": "success",
            "files": files
        }

    def _get_test_path(self, file_path: str) -> Optional[str]:
        """Get the test file path for a given file."""
        path = Path(file_path)
        if ".test." in path.name:
            return None
            
        if path.suffix in [".tsx", ".ts", ".jsx", ".js"]:
            return str(path.parent / f"{path.stem}.test{path.suffix}")
        elif path.suffix == ".py":
            return str(path.parent / f"test_{path.stem}.py")
        return None

    def _generate_test_content(self, file_path: str) -> str:
        """Generate test content for a file."""
        path = Path(file_path)
        if path.suffix in [".tsx", ".jsx"]:
            component_name = path.stem
            return f"""import {{ render, screen }} from '@testing-library/react'
import {{ {component_name} }} from './{component_name}'

describe('{component_name}', () => {{
    it('renders correctly', () => {{
        render(<{component_name} />)
        // Add assertions here
    }})
}})
"""
        elif path.suffix in [".ts", ".js"]:
            module_name = path.stem
            return f"""import {{ {module_name} }} from './{module_name}'

describe('{module_name}', () => {{
    it('works correctly', () => {{
        // Add test cases here
    }})
}})
"""
        elif path.suffix == ".py":
            module_name = path.stem
            return f"""import unittest
from {module_name} import *

class Test{module_name.title()}(unittest.TestCase):
    def test_functionality(self):
        # Add test cases here
        pass

if __name__ == '__main__':
    unittest.main()
"""
        return ""

    def _validate_naming_convention(self, name: str, domain: str) -> bool:
        """Validate component name against domain naming convention."""
        convention = self.tree_focus[domain]["naming_conventions"]["components"]
        
        if convention == "PascalCase":
            return name[0].isupper() and "_" not in name
        elif convention == "camelCase":
            return name[0].islower() and "_" not in name
        elif convention == "kebab-case":
            return name.islower() and "_" not in name and "-" in name
        elif convention == "snake_case":
            return name.islower() and "_" in name
        
        return True 