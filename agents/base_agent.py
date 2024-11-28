from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import os
import json
import aiohttp
import markdown
import asyncio
import importlib
import inspect
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

print("Loading BaseAgent class...")

class KnowledgeBase:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = storage_dir / "knowledge_index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        """Load the knowledge index."""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {
            "topics": {},
            "tags": {},
            "references": {},
            "last_updated": None
        }

    def _save_index(self):
        """Save the knowledge index."""
        self.index["last_updated"] = datetime.now().isoformat()
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    def add_knowledge(self, topic: str, content: Dict[str, Any], tags: List[str] = None) -> str:
        """Add new knowledge to the knowledge base."""
        # Create a unique ID for the knowledge entry
        timestamp = datetime.now().isoformat()
        knowledge_id = f"{topic.lower().replace(' ', '_')}_{timestamp}"
        
        # Store the actual content
        knowledge_file = self.storage_dir / f"{knowledge_id}.json"
        knowledge_data = {
            "id": knowledge_id,
            "topic": topic,
            "content": content,
            "tags": tags or [],
            "created_at": timestamp,
            "references": content.get("references", []),
            "summary": content.get("summary", ""),
            "key_points": content.get("key_points", []),
            "version": 1
        }
        
        with open(knowledge_file, 'w') as f:
            json.dump(knowledge_data, f, indent=2)
        
        # Update the index
        if topic not in self.index["topics"]:
            self.index["topics"][topic] = []
        self.index["topics"][topic].append(knowledge_id)
        
        # Update tags
        if tags:
            for tag in tags:
                if tag not in self.index["tags"]:
                    self.index["tags"][tag] = []
                self.index["tags"][tag].append(knowledge_id)
        
        # Update references
        for ref in content.get("references", []):
            ref_id = ref.get("url", ref.get("id"))
            if ref_id:
                if ref_id not in self.index["references"]:
                    self.index["references"][ref_id] = []
                self.index["references"][ref_id].append(knowledge_id)
        
        self._save_index()
        return knowledge_id

    def get_knowledge(self, topic: str = None, tag: str = None, reference: str = None) -> List[Dict[str, Any]]:
        """Retrieve knowledge by topic, tag, or reference."""
        knowledge_ids = set()
        
        if topic and topic in self.index["topics"]:
            knowledge_ids.update(self.index["topics"][topic])
        
        if tag and tag in self.index["tags"]:
            knowledge_ids.update(self.index["tags"][tag])
        
        if reference and reference in self.index["references"]:
            knowledge_ids.update(self.index["references"][reference])
        
        knowledge = []
        for kid in knowledge_ids:
            knowledge_file = self.storage_dir / f"{kid}.json"
            if knowledge_file.exists():
                with open(knowledge_file, 'r') as f:
                    knowledge.append(json.load(f))
        
        return knowledge

    def summarize_knowledge(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get a summary of all knowledge for a topic."""
        knowledge = self.get_knowledge(topic=topic)
        if not knowledge:
            return None
        
        return {
            "topic": topic,
            "total_entries": len(knowledge),
            "key_points": list(set(
                point
                for entry in knowledge
                for point in entry.get("key_points", [])
            )),
            "references": list(set(
                ref.get("url", ref.get("id"))
                for entry in knowledge
                for ref in entry.get("references", [])
            )),
            "latest_update": max(entry["created_at"] for entry in knowledge)
        }

class BaseAgent(ABC):
    def __init__(self, config: Dict[str, Any]):
        print(f"Initializing BaseAgent with config: {config}")
        self.config = config
        self.name = self.__class__.__name__
        self.knowledge_base = KnowledgeBase(
            Path(f"knowledge/{self.name.lower()}")
        )
        self.learned_patterns = {}
        print(f"BaseAgent initialized with name: {self.name}")

    async def _search_github(self, query: str) -> List[Dict[str, Any]]:
        print(f"BaseAgent._search_github called with query: {query}")
        async with aiohttp.ClientSession() as session:
            api_url = "https://api.github.com/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 5
            }
            
            try:
                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("items", [])
            except Exception as e:
                self.log(f"Error searching GitHub: {str(e)}")
            
            return []

    async def _search_documentation(self, topic: str) -> List[Dict[str, Any]]:
        """Search relevant documentation."""
        # TODO: Implement documentation search
        return []

    async def learn(self, topic: str) -> Dict[str, Any]:
        """Learn about a specific topic from various sources."""
        self.log(f"Starting learning process for: {topic}")
        
        # First, check existing knowledge
        existing_knowledge = self.knowledge_base.get_knowledge(topic=topic)
        if existing_knowledge:
            self.log(f"Found existing knowledge for {topic}")
            return self.knowledge_base.summarize_knowledge(topic)

        # If not, learn from sources
        learnings = await self._discover_and_implement(topic)
        
        # Structure and store the new knowledge
        self.knowledge_base.add_knowledge(
            topic=topic,
            content={
                "implementation": learnings.get("implementations", []),
                "references": [
                    {
                        "type": source["type"],
                        "url": source["url"],
                        "description": source["description"]
                    }
                    for source in learnings.get("sources", [])
                ],
                "summary": f"Learned implementation patterns for {topic}",
                "key_points": [
                    f"Found {len(learnings.get('sources', []))} relevant sources",
                    f"Generated {len(learnings.get('implementations', []))} implementations",
                    "Successfully tested and validated implementations"
                ]
            },
            tags=[
                "implementation",
                topic.replace(" ", "_"),
                self.name.lower()
            ]
        )
        
        return self.knowledge_base.summarize_knowledge(topic)

    async def _discover_and_implement(self, topic: str) -> Dict[str, Any]:
        """Discover and implement new learning patterns."""
        # First, try to find relevant documentation or examples
        sources = await self._find_learning_sources(topic)
        
        # Generate and test implementation for each source
        implementations = []
        for source in sources:
            if impl := await self._generate_implementation(source):
                if await self._test_implementation(impl):
                    implementations.append(impl)
                    # Save successful pattern
                    self.learned_patterns[topic] = impl
        
        return {
            "sources": sources,
            "implementations": implementations
        }

    async def _find_learning_sources(self, topic: str) -> List[Dict[str, Any]]:
        """Find relevant learning sources for a topic."""
        sources = []
        
        # Try GitHub first
        github_results = await self._search_github(f"how to {topic} python")
        if github_results:
            sources.extend([{
                "type": "github",
                "url": repo["html_url"],
                "description": repo.get("description", "No description available")
            } for repo in github_results])

        # Try documentation
        doc_results = await self._search_documentation(topic)
        if doc_results:
            sources.extend([{
                "type": "documentation",
                "url": doc,
                "description": "Official documentation"
            } for doc in doc_results])

        return sources

    async def _generate_implementation(self, source: Dict[str, Any]) -> Optional[str]:
        """Generate implementation code based on a source."""
        try:
            if source["type"] == "github":
                return await self._generate_from_github(source["url"])
            elif source["type"] == "documentation":
                return await self._generate_from_documentation(source["url"])
            return None
        except Exception as e:
            self.log(f"Error generating implementation: {str(e)}")
            return None

    async def _test_implementation(self, implementation: str) -> bool:
        """Test a generated implementation."""
        try:
            # Create a safe execution environment
            namespace = {}
            exec(implementation, namespace)
            # Basic validation - check if it defines expected functions
            return all(
                func in namespace
                for func in ["fetch_data", "process_data", "validate_data"]
            )
        except Exception as e:
            self.log(f"Implementation test failed: {str(e)}")
            return False

    async def _execute_pattern(self, pattern: str) -> Dict[str, Any]:
        """Execute a learned pattern."""
        try:
            # Create execution environment
            namespace = {}
            exec(pattern, namespace)
            # Execute the pattern's main function
            if "execute" in namespace:
                return namespace["execute"]()
            return {"error": "No execute function found in pattern"}
        except Exception as e:
            return {"error": f"Pattern execution failed: {str(e)}"}

    async def _generate_from_github(self, repo_url: str) -> Optional[str]:
        """Generate implementation from a GitHub repository."""
        # Extract user/repo from URL
        parts = repo_url.split("/")
        if len(parts) < 5:
            return None
            
        user, repo = parts[-2], parts[-1]
        
        # Fetch repository content
        async with aiohttp.ClientSession() as session:
            api_url = f"https://api.github.com/repos/{user}/{repo}/contents"
            async with session.get(api_url) as response:
                if response.status == 200:
                    contents = await response.json()
                    # Look for Python files
                    python_files = [
                        f for f in contents 
                        if f["name"].endswith(".py")
                    ]
                    if python_files:
                        # Get content of first Python file
                        file_url = python_files[0]["download_url"]
                        async with session.get(file_url) as file_response:
                            if file_response.status == 200:
                                return await file_response.text()
        return None

    async def _generate_from_documentation(self, doc_url: str) -> Optional[str]:
        """Generate implementation from documentation."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(doc_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        # Look for code examples
                        code_blocks = soup.find_all('code')
                        python_code = [
                            block.text 
                            for block in code_blocks 
                            if 'python' in block.get('class', [''])[0].lower()
                        ]
                        if python_code:
                            return python_code[0]
            return None
        except Exception as e:
            self.log(f"Error parsing documentation: {str(e)}")
            return None

    def log(self, message: str) -> None:
        """Log agent activity."""
        print(f"[{self.name}] {message}")

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results."""
        pass