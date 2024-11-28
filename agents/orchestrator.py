from typing import Dict, Any, List
import asyncio
import yaml
from pathlib import Path
from .base_agent import BaseAgent
from .developer import DeveloperAgent
from .reviewer import ReviewerAgent

class WorkflowError(Exception):
    """Custom exception for workflow errors."""
    pass

class OrchestratorAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config = self._load_config()
        self.workflows = self.config.get("workflows", {})
        self.developer = DeveloperAgent(config)
        self.reviewer = ReviewerAgent(config)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            return {}
        
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        workflow_name = input_data.get("workflow")
        if not workflow_name or workflow_name not in self.workflows:
            raise WorkflowError(f"Unknown workflow: {workflow_name}")

        workflow = self.workflows[workflow_name]
        return await self._execute_workflow(workflow, input_data)

    async def _execute_workflow(self, workflow: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow based on its definition."""
        results = []
        current_state = input_data.copy()

        print(f"Starting workflow execution with input: {input_data}")
        print(f"Workflow steps: {workflow['steps']}")

        for step in workflow["steps"]:
            step_type = step["type"]
            agent = step.get("agent", "developer")
            
            print(f"\nExecuting step: {step_type} with agent: {agent}")
            print(f"Current state: {current_state}")
            
            try:
                # Prepare input for agent
                agent_input = {
                    "action": step_type,
                    **step.get("params", {}),
                    **current_state
                }

                print(f"Agent input: {agent_input}")

                # Add code for review if needed
                if step_type == "review_code":
                    files = []
                    for file_path in current_state.get("files", []):
                        try:
                            with open(file_path, "r") as f:
                                content = f.read()
                                files.append({
                                    "path": file_path,
                                    "content": content
                                })
                        except Exception as e:
                            print(f"Failed to read file {file_path}: {str(e)}")
                            continue
                    
                    agent_input["code"] = {
                        "files": files
                    }
                    print(f"Added code for review: {agent_input['code']}")
                elif step_type == "verify_fix":
                    agent_input["fix"] = {
                        "files": current_state.get("files", []),
                        "update_tests": current_state.get("issue", {}).get("update_tests", False)
                    }
                    print(f"Added fix for verification: {agent_input['fix']}")

                # Execute agent action
                if agent == "developer":
                    result = await self.developer.process(agent_input)
                elif agent == "reviewer":
                    result = await self.reviewer.process(agent_input)
                else:
                    return {
                        "status": "error",
                        "error": f"Unknown agent type: {agent}",
                        "partial_results": results
                    }

                print(f"Agent result: {result}")

                # Handle agent result
                if result.get("status") == "error":
                    if "Invalid naming convention" in result.get("error", "") or "Invalid file path" in result.get("error", ""):
                        return {
                            "status": "review_failed",
                            "step": step_type,
                            "review_feedback": [result.get("error")],
                            "partial_results": results
                        }
                    else:
                        print(f"Error in step {step_type}: {result.get('error')}")
                        return {
                            "status": "error",
                            "error": f"Workflow failed at step {step_type}",
                            "details": result.get("error"),
                            "partial_results": results
                        }
                elif result.get("status") == "failed":
                    print(f"Step {step_type} failed validation: {result.get('issues', [])}")
                    return {
                        "status": "review_failed",
                        "step": step_type,
                        "review_feedback": result.get("issues", []),
                        "partial_results": results
                    }

                results.append({
                    "step": step_type,
                    "agent": agent,
                    "result": result
                })

                # Update current state with step results
                updates = self._extract_state_updates(step, result)
                current_state.update(updates)
                print(f"Updated state: {current_state}")

                # Check if we need to wait for review
                if step.get("require_review", False):
                    print(f"Performing review for step {step_type}")
                    review_result = await self._perform_review(result, step)
                    print(f"Review result: {review_result}")
                    if not review_result.get("approved", False):
                        return {
                            "status": "review_failed",
                            "step": step_type,
                            "review_feedback": review_result.get("feedback"),
                            "partial_results": results
                        }

            except Exception as e:
                print(f"Exception in step {step_type}: {str(e)}")
                return {
                    "status": "error",
                    "error": f"Workflow step {step_type} failed",
                    "details": str(e),
                    "partial_results": results
                }

        print("\nWorkflow completed successfully")
        return {
            "status": "completed",
            "results": results
        }

    def _extract_state_updates(self, step: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant state updates from step result."""
        updates = {}
        
        # Extract specified outputs
        for output_key in step.get("outputs", []):
            if output_key in result:
                updates[output_key] = result[output_key]

        # Add any files created or modified
        if "files" in result:
            updates["files"] = result["files"]
        if "created" in result:
            updates["created_files"] = result["created"]
        if "updated" in result:
            updates["updated_files"] = result["updated"]

        return updates

    async def _perform_review(self, result: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
        """Perform review of step results."""
        review_type = step.get("review_type", "code_review")
        
        review_input = {
            "action": review_type,
            "code": {
                "files": []
            }
        }

        # Prepare files for review
        if "files" in result:
            review_input["code"]["files"].extend(self._prepare_files_for_review(result["files"]))
        if "created" in result:
            review_input["code"]["files"].extend(self._prepare_files_for_review(result["created"]))
        if "updated" in result:
            review_input["code"]["files"].extend(self._prepare_files_for_review(result["updated"]))

        # Add any specific review parameters
        review_input.update(step.get("review_params", {}))

        # Perform the review
        review_result = await self.reviewer.process(review_input)

        # Check if review passed
        if review_result.get("status") == "failed":
            return {
                "approved": False,
                "feedback": review_result.get("issues", [])
            }

        return {
            "approved": True,
            "feedback": review_result.get("suggestions", [])
        }

    def _prepare_files_for_review(self, files: List[str]) -> List[Dict[str, Any]]:
        """Prepare files for review by reading their content."""
        prepared_files = []
        
        for file_path in files:
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                    prepared_files.append({
                        "path": file_path,
                        "content": content
                    })
            except Exception as e:
                self.log(f"Failed to read file {file_path}: {str(e)}")
                continue

        return prepared_files 