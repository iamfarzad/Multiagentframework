# Multi-Agent Framework Examples

This directory contains example usage of the Multi-Agent Framework.

## Examples

### create_component.py
Shows how to:
- Initialize the orchestrator
- Create a new React component
- Run code review
- Handle validation results

```python
import asyncio
from multiagentframework import OrchestratorAgent

async def main():
    orchestrator = OrchestratorAgent(config)
    result = await orchestrator.process({
        "workflow": "create_feature",
        "component": {
            "name": "UserProfile",
            "domain": "frontend",
            "files": [...]
        }
    })
```

## Adding New Examples

1. Create a new Python file in this directory
2. Add clear comments explaining the example
3. Update this README with a description
4. Ensure the example runs with the default config

## Running Examples

```bash
# Run specific example
python examples/create_component.py

# Run all examples
python -m pytest examples/
``` 