from typing import Dict, Any, List, Optional
import os
import json
import yaml
import aiohttp
import asyncio
from pathlib import Path
from .base_agent import BaseAgent

class ReviewerAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config = self._load_config()
        self.tree_focus = self.config.get("tree_focus", {})
        self.review_rules = self.config.get("agents", {}).get("reviewer", {}).get("review_rules", {})
        self.allowed_actions = self.config.get("agents", {}).get("reviewer", {}).get("allowed_actions", [])

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

        if action == "review_code":
            return await self._review_code(input_data["code"])
        elif action == "verify_fix":
            return await self._verify_fix(input_data["fix"])
        return {"error": "Unknown action"}

    async def _review_code(self, code: Dict[str, Any]) -> Dict[str, Any]:
        """Review code for best practices and potential issues."""
        review_results = {
            "status": "success",
            "issues": [],
            "suggestions": [],
            "best_practices": [],
            "domain_validations": {}
        }

        # Check files against domain boundaries
        for file in code.get("files", []):
            file_path = file.get("path", "")
            domain = self._get_file_domain(file_path)
            
            if not domain:
                review_results["issues"].append({
                    "type": "domain_boundary",
                    "file": file_path,
                    "message": "File does not belong to any defined domain"
                })
                continue

            # Check if path follows domain rules
            if not any(file_path.startswith(dir) for dir in self.tree_focus[domain]["directories"]):
                review_results["issues"].append({
                    "type": "file_path",
                    "file": file_path,
                    "message": f"File must be in one of {self.tree_focus[domain]['directories']}"
                })

            # Validate file size
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                if size > self.review_rules.get("max_file_size", 1000000):
                    review_results["issues"].append({
                        "type": "file_size",
                        "file": file_path,
                        "message": f"File size ({size} bytes) exceeds maximum allowed ({self.review_rules['max_file_size']} bytes)"
                    })

            # Domain-specific validations
            domain_validation = await self._validate_domain_specific(file, domain)
            review_results["domain_validations"][file_path] = domain_validation

            # Check function length
            if "functions" in file:
                for func in file["functions"]:
                    if len(func.get("body", "").split("\n")) > self.review_rules.get("max_function_length", 50):
                        review_results["issues"].append({
                            "type": "function_length",
                            "file": file_path,
                            "function": func["name"],
                            "message": f"Function exceeds maximum length of {self.review_rules['max_function_length']} lines"
                        })

        # Check test coverage if required
        if self.review_rules.get("required_tests", True):
            coverage = await self._check_test_coverage(code.get("files", []))
            if coverage < self.review_rules.get("coverage_threshold", 80):
                review_results["issues"].append({
                    "type": "test_coverage",
                    "message": f"Test coverage ({coverage}%) is below threshold ({self.review_rules['coverage_threshold']}%)"
                })

        if review_results["issues"]:
            review_results["status"] = "failed"
            return {
                "status": "review_failed",
                "review_feedback": review_results["issues"],
                "suggestions": review_results["suggestions"]
            }

        return review_results

    async def _verify_deployment(self, deployment: Dict[str, Any]) -> Dict[str, Any]:
        if deployment.get("error"):
            return {"status": "failed", "reason": deployment["error"]}

        # Check if services are responding
        health_checks = {}
        
        if "backend" in deployment["processes"]:
            health_checks["backend"] = {
                "status": await self._check_health(
                    deployment["processes"]["backend"]["url"],
                    domain="backend"
                ),
                "pid": deployment["processes"]["backend"]["pid"]
            }
        
        if "frontend" in deployment["processes"]:
            health_checks["frontend"] = {
                "status": await self._check_health(
                    deployment["processes"]["frontend"]["url"],
                    domain="frontend"
                ),
                "pid": deployment["processes"]["frontend"]["pid"]
            }

        # Check if all required services are healthy
        unhealthy_services = {
            service: details for service, details in health_checks.items()
            if not details["status"]
        }

        if unhealthy_services:
            # Try to get process logs for unhealthy services
            logs = await self._get_process_logs(unhealthy_services)
            return {
                "status": "failed",
                "reason": "Health check failed",
                "details": {
                    "health_checks": health_checks,
                    "logs": logs
                }
            }

        return {
            "status": "verified",
            "details": health_checks
        }

    async def _check_health(self, url: str, domain: str) -> bool:
        """Check health of a service with domain-specific checks."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False
                    
                    # Domain-specific health checks
                    if domain == "backend":
                        data = await response.json()
                        return data.get("status") == "healthy"
                    elif domain == "frontend":
                        text = await response.text()
                        return "<title>" in text.lower()
                    
                    return True
        except Exception:
            return False

    def _get_file_domain(self, file_path: str) -> Optional[str]:
        """Get the domain for a file based on its path."""
        for domain, rules in self.tree_focus.items():
            if any(file_path.startswith(dir) for dir in rules["directories"]):
                return domain
        return None

    async def _validate_domain_specific(self, file: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Validate a file against domain-specific rules."""
        validation = {
            "status": "valid",
            "issues": [],
            "suggestions": []
        }

        # Check file path follows naming convention
        path = Path(file["path"])
        if domain == "frontend":
            if not path.stem[0].isupper() and path.suffix in [".tsx", ".jsx"]:
                validation["issues"].append("Component files should use PascalCase")
            elif path.stem[0].isupper() and path.suffix in [".ts", ".js"]:
                validation["issues"].append("Utility files should use camelCase")
        elif domain == "backend":
            if path.stem[0].isupper() and not any(c.isupper() for c in path.stem[1:]):
                validation["issues"].append("Python files should use snake_case")

        # Check content follows domain conventions
        content = file["content"]
        if domain == "frontend":
            if "class " in content and not "React.Component" in content:
                validation["suggestions"].append("Consider using functional components instead of classes")
            if "var " in content:
                validation["suggestions"].append("Use const or let instead of var")
        elif domain == "backend":
            if "print(" in content:
                validation["suggestions"].append("Consider using logging instead of print statements")
            if "except:" in content:
                validation["suggestions"].append("Avoid bare except clauses")

        if validation["issues"]:
            validation["status"] = "invalid"

        return validation

    async def _check_test_coverage(self, files: List[str]) -> float:
        """Calculate test coverage for a set of files."""
        # This is a simplified implementation
        test_files = [f for f in files if ".test." in f or "test_" in f]
        return 100.0 if test_files else 0.0

    async def _verify_fix(self, fix: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a fix implementation."""
        review_results = {
            "status": "success",
            "issues": [],
            "suggestions": [],
            "best_practices": [],
            "domain_validations": {}
        }

        # Check files
        for file_path in fix.get("files", []):
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                    domain = self._get_file_domain(file_path)
                    
                    if not domain:
                        review_results["issues"].append({
                            "type": "domain_boundary",
                            "file": file_path,
                            "message": "File does not belong to any defined domain"
                        })
                        continue

                    # Validate file size
                    size = os.path.getsize(file_path)
                    if size > self.review_rules.get("max_file_size", 1000000):
                        review_results["issues"].append({
                            "type": "file_size",
                            "file": file_path,
                            "message": f"File size ({size} bytes) exceeds maximum allowed ({self.review_rules['max_file_size']} bytes)"
                        })

                    # Domain-specific validations
                    domain_validation = await self._validate_domain_specific({
                        "path": file_path,
                        "content": content
                    }, domain)
                    review_results["domain_validations"][file_path] = domain_validation

            except Exception as e:
                review_results["issues"].append({
                    "type": "file_error",
                    "file": file_path,
                    "message": f"Failed to read file: {str(e)}"
                })

        # Check test coverage if required
        if fix.get("update_tests", False) and self.review_rules.get("required_tests", True):
            coverage = await self._check_test_coverage(fix.get("files", []))
            if coverage < self.review_rules.get("coverage_threshold", 80):
                review_results["issues"].append({
                    "type": "test_coverage",
                    "message": f"Test coverage ({coverage}%) is below threshold ({self.review_rules['coverage_threshold']}%)"
                })

        if review_results["issues"]:
            review_results["status"] = "failed"

        return review_results 