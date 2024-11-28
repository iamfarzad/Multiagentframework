import yaml
import asyncio
from typing import Dict, Any, Type, List
from pathlib import Path

from agents.architect import ArchitectAgent
from agents.developer import DeveloperAgent
from agents.reviewer import ReviewerAgent
from agents.ux_ui import UXUIAgent
from agents.base_agent import BaseAgent

class Orchestrator:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.agents = self._initialize_agents()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _initialize_agents(self) -> Dict[str, BaseAgent]:
        """Initialize all agents based on configuration."""
        agent_classes: Dict[str, Type[BaseAgent]] = {
            "architect": ArchitectAgent,
            "developer": DeveloperAgent,
            "reviewer": ReviewerAgent,
            "ux_ui": UXUIAgent
        }
        
        agents = {}
        for agent_name, agent_config in self.config.get("agents", {}).items():
            if agent_config.get("enabled", True):
                agent_class = agent_classes.get(agent_name)
                if agent_class:
                    agents[agent_name] = agent_class(agent_config)
        
        return agents
    
    async def learn_task(self, topic: str) -> Dict[str, Any]:
        """Coordinate learning across all agents for a specific topic."""
        learning_results = {}
        
        # Each agent learns about the topic
        for agent_name, agent in self.agents.items():
            self.log(f"Agent {agent_name} is learning about: {topic}")
            learning_results[agent_name] = await agent.learn(topic)
        
        return learning_results
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task through the agent pipeline."""
        results = {}
        
        # First, let agents learn about the task if needed
        if task_data.get("requires_learning"):
            learning_results = await self.learn_task(task_data["topic"])
            results["learning"] = learning_results
        
        # Architecture phase
        if "architect" in self.agents:
            results["architecture"] = await self.agents["architect"].process(task_data)
        
        # Development phase
        if "developer" in self.agents:
            dev_input = {**task_data, **results.get("architecture", {})}
            results["development"] = await self.agents["developer"].process(dev_input)
        
        # Review phase
        if "reviewer" in self.agents:
            review_input = {**task_data, **results.get("development", {})}
            results["review"] = await self.agents["reviewer"].process(review_input)
        
        # UX/UI phase
        if "ux_ui" in self.agents:
            ui_input = {**task_data, **results.get("architecture", {})}
            results["ux_ui"] = await self.agents["ux_ui"].process(ui_input)
        
        return results

    def log(self, message: str) -> None:
        """Log orchestrator activity."""
        print(f"[Orchestrator] {message}")

async def main():
    orchestrator = Orchestrator()
    
    # Example task with learning requirement
    task = {
        "project_name": "AI Model Deployment",
        "requires_learning": True,
        "topic": "FastAPI and Azure AI Studio deployment",
        "project_requirements": {
            "description": "Create a sample AI model deployment application",
            "features": ["model deployment", "API endpoints", "monitoring"]
        }
    }
    
    results = await orchestrator.process_task(task)
    print("Task processing completed:", results)

if __name__ == "__main__":
    asyncio.run(main()) 