import unittest
import asyncio
import yaml
from pathlib import Path
from agents.orchestrator import OrchestratorAgent

class TestOrchestratorAgent(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.test_config = {
            "tree_focus": {
                "frontend": {
                    "directories": ["src/", "components/"],
                    "extensions": [".tsx", ".ts", ".css"],
                    "naming_conventions": {
                        "components": "PascalCase",
                        "files": "kebab-case"
                    }
                },
                "backend": {
                    "directories": ["api/", "server/"],
                    "extensions": [".py"],
                    "naming_conventions": {
                        "modules": "snake_case",
                        "classes": "PascalCase"
                    }
                }
            },
            "workflows": {
                "create_feature": {
                    "steps": [
                        {
                            "type": "create_component",
                            "agent": "developer",
                            "params": {
                                "domain": "frontend"
                            },
                            "require_review": True
                        },
                        {
                            "type": "review_code",
                            "agent": "reviewer",
                            "review_type": "domain_validation"
                        }
                    ]
                },
                "fix_issue": {
                    "steps": [
                        {
                            "type": "fix_issue",
                            "agent": "developer",
                            "params": {
                                "update_tests": True
                            }
                        },
                        {
                            "type": "verify_fix",
                            "agent": "reviewer"
                        }
                    ]
                }
            },
            "agents": {
                "developer": {
                    "allowed_actions": ["create_component", "fix_issue"],
                    "domain_rules": {
                        "frontend": {
                            "require_tests": True,
                            "max_file_size": 1000000,
                            "max_function_length": 50
                        }
                    }
                },
                "reviewer": {
                    "allowed_actions": ["review_code", "verify_fix"],
                    "review_rules": {
                        "coverage_threshold": 80,
                        "max_file_size": 1000000,
                        "max_function_length": 50
                    }
                }
            }
        }
        
        # Save test config
        Path("config").mkdir(exist_ok=True)
        with open("config/config.yaml", "w") as f:
            yaml.dump(self.test_config, f)
        
        self.orchestrator = OrchestratorAgent(self.test_config)

    def tearDown(self):
        """Clean up test environment."""
        try:
            Path("config/config.yaml").unlink()
            Path("config").rmdir()
        except:
            pass

    async def async_test_workflow_execution(self):
        """Test workflow execution."""
        # Test create_feature workflow
        feature_result = await self.orchestrator.process({
            "workflow": "create_feature",
            "component": {
                "name": "TestComponent",
                "domain": "frontend",
                "files": [
                    {
                        "path": "src/components/TestComponent/TestComponent.tsx",
                        "type": "component",
                        "content": "function TestComponent() { return <div>Test</div> }"
                    }
                ]
            }
        })
        
        self.assertEqual(feature_result["status"], "completed")
        self.assertTrue(len(feature_result["results"]) > 0)
        
        # Test fix_issue workflow
        issue_result = await self.orchestrator.process({
            "workflow": "fix_issue",
            "issue": {
                "files": [
                    {
                        "path": "src/components/TestComponent/TestComponent.tsx",
                        "type": "component",
                        "content": "function TestComponent() { return <div>Fixed</div> }"
                    }
                ],
                "update_tests": True
            }
        })
        
        self.assertEqual(issue_result["status"], "completed")
        self.assertTrue(len(issue_result["results"]) > 0)

    def test_workflow_execution(self):
        """Wrapper for async workflow test."""
        asyncio.run(self.async_test_workflow_execution())

    async def async_test_review_gates(self):
        """Test review gates in workflows."""
        result = await self.orchestrator.process({
            "workflow": "create_feature",
            "component": {
                "name": "InvalidComponent",
                "domain": "frontend",
                "files": [
                    {
                        "path": "wrong/path/Component.tsx",
                        "type": "component",
                        "content": "function Component() { return <div>Invalid</div> }"
                    }
                ]
            }
        })
        
        self.assertEqual(result["status"], "review_failed")
        self.assertIn("review_feedback", result)

    def test_review_gates(self):
        """Wrapper for async review gates test."""
        asyncio.run(self.async_test_review_gates())

    async def async_test_domain_validation(self):
        """Test domain validation."""
        result = await self.orchestrator.process({
            "workflow": "create_feature",
            "component": {
                "name": "test_component",  # Invalid naming convention
                "domain": "frontend",
                "files": [
                    {
                        "path": "src/components/test_component/test_component.tsx",
                        "type": "component",
                        "content": "function test_component() { return <div>Test</div> }"
                    }
                ]
            }
        })
        
        self.assertEqual(result["status"], "review_failed")
        self.assertTrue(any("naming convention" in str(feedback).lower() 
                          for feedback in result["review_feedback"]))

    def test_domain_validation(self):
        """Wrapper for async domain validation test."""
        asyncio.run(self.async_test_domain_validation())

    def test_config_loading(self):
        """Test configuration loading."""
        self.assertIsNotNone(self.orchestrator.config)
        self.assertIn("workflows", self.orchestrator.config)
        self.assertIn("tree_focus", self.orchestrator.config)
        self.assertIn("agents", self.orchestrator.config)

    def test_workflow_validation(self):
        """Test workflow validation."""
        invalid_workflow = {
            "workflow": "non_existent_workflow",
            "component": {
                "name": "TestComponent",
                "domain": "frontend"
            }
        }
        
        with self.assertRaises(Exception):
            asyncio.run(self.orchestrator.process(invalid_workflow))

if __name__ == "__main__":
    unittest.main() 