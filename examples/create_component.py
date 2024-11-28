import asyncio
from multiagentframework import OrchestratorAgent

async def main():
    # Initialize the orchestrator with your config
    config = {
        "tree_focus": {
            "frontend": {
                "directories": ["src/", "components/"],
                "extensions": [".tsx", ".ts", ".css"],
                "naming_conventions": {
                    "components": "PascalCase",
                    "files": "kebab-case"
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
            }
        },
        "agents": {
            "developer": {
                "allowed_actions": ["create_component"],
                "domain_rules": {
                    "frontend": {
                        "require_tests": True,
                        "max_file_size": 1000000,
                        "max_function_length": 50
                    }
                }
            },
            "reviewer": {
                "allowed_actions": ["review_code"],
                "review_rules": {
                    "coverage_threshold": 80,
                    "max_file_size": 1000000,
                    "max_function_length": 50
                }
            }
        }
    }
    
    orchestrator = OrchestratorAgent(config)

    # Create a new component
    result = await orchestrator.process({
        "workflow": "create_feature",
        "component": {
            "name": "UserProfile",
            "domain": "frontend",
            "files": [
                {
                    "path": "src/components/UserProfile/UserProfile.tsx",
                    "type": "component",
                    "content": """
import React from 'react'

export function UserProfile({ name, email }) {
    return (
        <div className="user-profile">
            <h2>{name}</h2>
            <p>{email}</p>
        </div>
    )
}
"""
                }
            ]
        }
    })

    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(main()) 