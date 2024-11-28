import asyncio
from orchestrator import Orchestrator

async def run_test_task():
    """Run a test task through the multi-agent framework."""
    # Initialize orchestrator
    orchestrator = Orchestrator()
    
    # Define a deployment task
    task = {
        "type": "deploy",
        "requirements": {
            "app_name": "test-app",
            "port": 3000,
            "environment": "development",
            "stack": {
                "frontend": "react",
                "backend": "fastapi"
            },
            "features": [
                "authentication",
                "dashboard",
                "api"
            ]
        }
    }
    
    try:
        # Process the task through all agents
        result = await orchestrator.process_task(task)
        print("\n=== Deployment Results ===")
        print(f"Status: {result.get('status', 'unknown')}")
        print("Details:", result.get("details", {}))
            
    except Exception as e:
        print(f"Error processing task: {str(e)}")

if __name__ == "__main__":
    print("Starting test task...")
    asyncio.run(run_test_task()) 