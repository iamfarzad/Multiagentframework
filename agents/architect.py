from typing import Dict, Any, List
import os
import json
import yaml
from pathlib import Path
from .base_agent import BaseAgent

class ArchitectAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config = self._load_config()
        self.tree_focus = self.config.get("tree_focus", {})
        self.validation_rules = self.config.get("agents", {}).get("architect", {}).get("validation_rules", {})

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            return {}
        
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action")
        if action not in self.config.get("agents", {}).get("architect", {}).get("allowed_actions", []):
            return {"error": f"Action not allowed: {action}"}

        if action == "validate_deployment":
            return await self._validate_deployment(input_data["requirements"])
        elif action == "design_architecture":
            return await self._design_architecture(input_data["requirements"])
        elif action == "analyze_structure":
            return await self._analyze_structure(input_data.get("path", "."))
        return {"error": "Unknown action"}

    def is_within_domain(self, file_path: str, domain: str) -> bool:
        """Check if file is within allowed domain boundaries."""
        if domain not in self.tree_focus:
            return False

        domain_config = self.tree_focus[domain]
        
        # Check directories
        if not any(file_path.startswith(dir) for dir in domain_config["directories"]):
            return False
        
        # Check extensions
        if not any(file_path.endswith(ext) for ext in domain_config["extensions"]):
            return False
        
        return True

    async def _validate_deployment(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        # Validate required fields
        required_fields = ["app_name", "port", "environment", "stack"]
        for field in required_fields:
            if field not in requirements:
                return {
                    "status": "invalid",
                    "reason": f"Missing required field: {field}"
                }

        # Validate port number using config rules
        port = requirements["port"]
        port_range = self.validation_rules.get("port_range", {"min": 1024, "max": 65535})
        if not isinstance(port, int) or port < port_range["min"] or port > port_range["max"]:
            return {
                "status": "invalid",
                "reason": f"Invalid port number. Must be between {port_range['min']} and {port_range['max']}"
            }

        # Validate environment using config rules
        valid_environments = self.validation_rules.get("environments", ["development", "staging", "production"])
        if requirements["environment"] not in valid_environments:
            return {
                "status": "invalid",
                "reason": f"Invalid environment. Must be one of: {', '.join(valid_environments)}"
            }

        # Analyze existing project structure
        project_analysis = await self._analyze_structure(".")
        if project_analysis["status"] == "invalid":
            return project_analysis

        # Generate tasks for the developer agent
        tasks = []
        
        # Check frontend dependencies
        if "frontend" in requirements["stack"]:
            frontend_deps = self.tree_focus["frontend"]["dependencies"]
            missing_deps = self._check_missing_dependencies(
                project_analysis["structure"]["frontend"].get("dependencies", []),
                frontend_deps["required"] + frontend_deps.get("ui_libraries", []) + frontend_deps.get("state_management", [])
            )
            if missing_deps:
                tasks.append({
                    "action": "update_dependencies",
                    "domain": "frontend",
                    "dependencies": missing_deps
                })

        # Check backend dependencies
        if "backend" in requirements["stack"]:
            backend_deps = self.tree_focus["backend"]["dependencies"]
            framework_deps = backend_deps["frameworks"] + backend_deps["databases"] + backend_deps["authentication"]
            missing_deps = self._check_missing_dependencies(
                project_analysis["structure"]["backend"].get("dependencies", []),
                framework_deps
            )
            if missing_deps:
                tasks.append({
                    "action": "update_dependencies",
                    "domain": "backend",
                    "dependencies": missing_deps
                })

        return {
            "status": "valid",
            "configuration": {
                "app_name": requirements["app_name"],
                "port": port,
                "environment": requirements["environment"],
                "stack": requirements["stack"]
            },
            "structure": project_analysis["structure"],
            "tasks": tasks
        }

    def _check_missing_dependencies(self, existing_deps: List[str], required_deps: List[str]) -> List[str]:
        """Check for missing dependencies."""
        return [dep for dep in required_deps if not any(existing.startswith(dep) for existing in existing_deps)]

    async def _analyze_structure(self, path: str) -> Dict[str, Any]:
        """Analyze project structure and validate against domain boundaries."""
        structure = {
            "frontend": {"exists": False, "framework": None, "dependencies": [], "files": []},
            "backend": {"exists": False, "framework": None, "dependencies": [], "files": []},
            "database": {"exists": False, "framework": None, "dependencies": [], "files": []}
        }

        # Walk through project files
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, path)

                # Check each domain
                for domain, domain_config in self.tree_focus.items():
                    if self.is_within_domain(relative_path, domain):
                        structure[domain]["exists"] = True
                        structure[domain]["files"].append(relative_path)

                        # Extract dependencies
                        if file == "package.json":
                            structure["frontend"].update(self._analyze_package_json(file_path))
                        elif file in ["requirements.txt", "pyproject.toml"]:
                            structure["backend"].update(self._analyze_python_deps(file_path))

        return {
            "status": "valid",
            "structure": structure
        }

    def _analyze_package_json(self, file_path: str) -> Dict[str, Any]:
        """Analyze package.json for frontend dependencies."""
        try:
            with open(file_path, "r") as f:
                package_json = json.load(f)
                deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
                
                framework = None
                if "react" in deps:
                    framework = "next" if "next" in deps else "react"
                elif "vue" in deps:
                    framework = "vue"

                return {
                    "framework": framework,
                    "dependencies": list(deps.keys())
                }
        except (json.JSONDecodeError, FileNotFoundError):
            return {"framework": None, "dependencies": []}

    def _analyze_python_deps(self, file_path: str) -> Dict[str, Any]:
        """Analyze Python dependencies."""
        try:
            if file_path.endswith("requirements.txt"):
                with open(file_path, "r") as f:
                    deps = [line.split("==")[0] for line in f.readlines() if "==" in line]
            else:  # pyproject.toml
                import toml
                with open(file_path, "r") as f:
                    pyproject = toml.load(f)
                    deps = list(pyproject.get("tool", {}).get("poetry", {}).get("dependencies", {}).keys())

            framework = None
            if "fastapi" in deps:
                framework = "fastapi"
            elif "flask" in deps:
                framework = "flask"
            elif "django" in deps:
                framework = "django"

            return {
                "framework": framework,
                "dependencies": deps
            }
        except Exception:
            return {"framework": None, "dependencies": []}

    async def _design_architecture(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Design the application architecture based on requirements."""
        stack = requirements.get("stack", {})
        features = requirements.get("features", [])
        
        architecture = {
            "frontend": self._design_frontend_architecture(stack.get("frontend"), features),
            "backend": self._design_backend_architecture(stack.get("backend"), features),
            "deployment": {
                "frontend": {
                    "port": requirements.get("port", 3000),
                    "environment": requirements.get("environment", "development")
                },
                "backend": {
                    "port": requirements.get("backend_port", 8000),
                    "environment": requirements.get("environment", "development")
                }
            }
        }

        return {
            "status": "designed",
            "architecture": architecture
        }

    def _design_frontend_architecture(self, frontend_type: str, features: list) -> Dict[str, Any]:
        """Design frontend architecture based on framework and features."""
        if not frontend_type:
            return None

        architecture = {
            "framework": frontend_type,
            "components": [
                {
                    "name": "App",
                    "type": "root",
                    "children": []
                }
            ],
            "routing": "file-based" if frontend_type == "next" else "react-router",
            "state_management": "react-query" if "api" in features else "react-context"
        }

        # Add common components based on features
        if "authentication" in features:
            architecture["components"].extend([
                {"name": "AuthProvider", "type": "context"},
                {"name": "LoginForm", "type": "form"},
                {"name": "ProtectedRoute", "type": "hoc"}
            ])

        if "dashboard" in features:
            architecture["components"].extend([
                {"name": "Dashboard", "type": "page"},
                {"name": "Sidebar", "type": "navigation"},
                {"name": "Header", "type": "navigation"}
            ])

        return architecture

    def _design_backend_architecture(self, backend_type: str, features: list) -> Dict[str, Any]:
        """Design backend architecture based on framework and features."""
        if not backend_type:
            return None

        architecture = {
            "framework": backend_type,
            "database": "sqlalchemy" if backend_type in ["fastapi", "flask"] else "django-orm",
            "authentication": "jwt",
            "endpoints": []
        }

        # Add common endpoints based on features
        if "authentication" in features:
            architecture["endpoints"].extend([
                {
                    "path": "/api/auth/login",
                    "methods": ["POST"],
                    "auth_required": False
                },
                {
                    "path": "/api/auth/register",
                    "methods": ["POST"],
                    "auth_required": False
                }
            ])

        if "dashboard" in features:
            architecture["endpoints"].extend([
                {
                    "path": "/api/dashboard",
                    "methods": ["GET"],
                    "auth_required": True
                }
            ])

        return architecture