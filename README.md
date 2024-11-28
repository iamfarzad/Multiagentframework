# Multi-Agent Framework

A Python framework for automated code generation, review, and validation using specialized agents.

## Overview

This framework provides a flexible system for automating software development tasks using specialized agents:
- Developer Agent: Creates and modifies code following domain rules
- Reviewer Agent: Validates code against standards and best practices
- Orchestrator: Manages workflows and agent coordination

## Features

- 🤖 Multiple specialized agents (Developer, Reviewer)
- 🔄 Configurable workflows
- ✅ Automated code review and validation
- 🧪 Test generation
- 📏 Domain-specific rules enforcement
- 🏗️ Component scaffolding

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/multiagentframework.git
cd multiagentframework
```

2. Install dependencies:
```bash
pip install -e .
```

## Quick Start

1. Create a `config.yaml` in your project:

```yaml
tree_focus:
  frontend:
    directories: ["src/", "components/"]
    extensions: [".tsx", ".ts", ".css"]
    naming_conventions:
      components: PascalCase
      files: kebab-case

workflows:
  create_feature:
    steps:
      - type: create_component
        agent: developer
        params:
          domain: frontend
        require_review: true
      - type: review_code
        agent: reviewer
        review_type: domain_validation

agents:
  developer:
    allowed_actions: ["create_component", "fix_issue"]
    domain_rules:
      frontend:
        require_tests: true
        max_file_size: 1000000
        max_function_length: 50
  reviewer:
    allowed_actions: ["review_code", "verify_fix"]
    review_rules:
      coverage_threshold: 80
      max_file_size: 1000000
      max_function_length: 50
```

2. Use in your code:

```python
import asyncio
from multiagentframework import OrchestratorAgent

async def main():
    # Initialize with your config
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

if __name__ == "__main__":
    asyncio.run(main())
```

## Project Structure

```
multiagentframework/
├── agents/                 # Agent implementations
│   ├── __init__.py
│   ├── base_agent.py      # Base agent class
│   ├── developer.py       # Developer agent
│   ├── reviewer.py        # Reviewer agent
│   └── orchestrator.py    # Workflow orchestrator
├── examples/              # Example usage
│   └── create_component.py
├── tests/                 # Test suite
│   └── test_orchestrator.py
├── config.yaml           # Default configuration
├── setup.py             # Package setup
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Adding New Agents
1. Create a new agent class inheriting from `BaseAgent`
2. Implement the `process` method
3. Add agent configuration to `config.yaml`

### Adding New Workflows
1. Define the workflow in `config.yaml`
2. Ensure required agent actions exist
3. Add any new agent capabilities needed

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- Use Python type hints
- Follow PEP 8 guidelines
- Add docstrings to all functions and classes
- Write unit tests for new features

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- Built with Python 3.7+
- Uses FastAPI for API examples
- Uses React and TypeScript for frontend examples 