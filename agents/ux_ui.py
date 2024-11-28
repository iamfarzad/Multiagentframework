from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
import aiohttp
from bs4 import BeautifulSoup
import re
import json

class UXUIAgent(BaseAgent):
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process UI/UX design tasks."""
        self.log(f"Designing UI for: {input_data.get('component_name', 'Unknown Component')}")
        
        # Learn design patterns if needed
        if input_data.get("requires_learning"):
            await self.learn_design_patterns(input_data.get("topic", ""))
        
        return await self._generate_design(input_data)

    async def learn_design_patterns(self, topic: str) -> Dict[str, Any]:
        """Learn UI/UX design patterns and best practices."""
        sources = await self._find_design_sources(topic)
        patterns = await self._extract_design_patterns(sources)
        
        # Update knowledge base
        self._update_knowledge_base(f"design_patterns_{topic}", {
            "sources": sources,
            "patterns": patterns
        })
        
        return patterns

    async def _find_design_sources(self, topic: str) -> List[Dict[str, Any]]:
        """Find UI/UX design specific sources."""
        sources = []
        
        # Search design systems
        design_system_results = await self._search_design_systems(topic)
        sources.extend(design_system_results)

        # Search component libraries
        component_results = await self._search_component_libraries(topic)
        sources.extend(component_results)

        # Search UX patterns
        pattern_results = await self._search_ux_patterns(topic)
        sources.extend(pattern_results)

        return sources

    async def _search_design_systems(self, topic: str) -> List[Dict[str, Any]]:
        """Search popular design systems."""
        systems = []
        
        # Popular design systems
        design_systems = [
            "https://material.io/design",
            "https://carbondesignsystem.com/",
            "https://primer.style/",
            "https://www.lightningdesignsystem.com/",
            "https://atlassian.design/"
        ]
        
        async with aiohttp.ClientSession() as session:
            for system in design_systems:
                try:
                    async with session.get(system) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Look for relevant components or patterns
                            components = soup.find_all(['section', 'article'], class_=['component', 'pattern'])
                            for component in components:
                                if topic.lower() in component.text.lower():
                                    systems.append({
                                        "type": "design_system",
                                        "url": system,
                                        "name": component.find(['h1', 'h2']).text if component.find(['h1', 'h2']) else "Design Component",
                                        "description": component.find('p').text if component.find('p') else "",
                                        "system_name": system.split("//")[1].split(".")[0]
                                    })
                except Exception as e:
                    self.log(f"Error searching design system {system}: {str(e)}")
        
        return systems

    async def _search_component_libraries(self, topic: str) -> List[Dict[str, Any]]:
        """Search UI component libraries."""
        components = []
        
        # Popular component libraries
        libraries = [
            "https://mui.com/components/",
            "https://ant.design/components/",
            "https://chakra-ui.com/docs/components",
            "https://tailwindui.com/components"
        ]
        
        async with aiohttp.ClientSession() as session:
            for library in libraries:
                try:
                    async with session.get(library) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Look for component documentation
                            component_docs = soup.find_all(['div', 'article'], class_=['component', 'docs'])
                            for doc in component_docs:
                                if topic.lower() in doc.text.lower():
                                    components.append({
                                        "type": "component",
                                        "url": library,
                                        "name": doc.find(['h1', 'h2']).text if doc.find(['h1', 'h2']) else "UI Component",
                                        "code": self._extract_component_code(doc),
                                        "library": library.split("//")[1].split(".")[0]
                                    })
                except Exception as e:
                    self.log(f"Error searching component library {library}: {str(e)}")
        
        return components

    async def _search_ux_patterns(self, topic: str) -> List[Dict[str, Any]]:
        """Search UX design patterns."""
        patterns = []
        
        # UX pattern resources
        pattern_sources = [
            "https://www.nngroup.com/articles/",
            "https://www.smashingmagazine.com/category/ux/",
            "https://uxplanet.org/"
        ]
        
        async with aiohttp.ClientSession() as session:
            for source in pattern_sources:
                try:
                    async with session.get(source) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Look for UX pattern articles
                            articles = soup.find_all(['article', 'div'], class_=['post', 'article'])
                            for article in articles:
                                if topic.lower() in article.text.lower():
                                    patterns.append({
                                        "type": "ux_pattern",
                                        "url": source,
                                        "title": article.find(['h1', 'h2']).text if article.find(['h1', 'h2']) else "UX Pattern",
                                        "summary": article.find('p').text if article.find('p') else "",
                                        "source": source.split("//")[1].split(".")[0]
                                    })
                except Exception as e:
                    self.log(f"Error searching UX patterns from {source}: {str(e)}")
        
        return patterns

    def _extract_component_code(self, doc_element: BeautifulSoup) -> Optional[str]:
        """Extract component implementation code."""
        code_block = doc_element.find('code')
        if code_block:
            return code_block.text
        return None

    async def _extract_design_patterns(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract design patterns from sources."""
        patterns = {
            "components": [],
            "ux_patterns": [],
            "design_guidelines": []
        }
        
        for source in sources:
            try:
                if source["type"] == "design_system":
                    system_patterns = await self._extract_from_design_system(source)
                    if system_patterns:
                        patterns["design_guidelines"].extend(system_patterns)
                
                elif source["type"] == "component":
                    component_patterns = self._extract_from_component(source)
                    if component_patterns:
                        patterns["components"].extend(component_patterns)
                
                elif source["type"] == "ux_pattern":
                    ux_patterns = self._extract_from_ux_pattern(source)
                    if ux_patterns:
                        patterns["ux_patterns"].extend(ux_patterns)
            
            except Exception as e:
                self.log(f"Error extracting patterns from {source['url']}: {str(e)}")
        
        return patterns

    async def _extract_from_design_system(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract patterns from design system documentation."""
        patterns = []
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(source["url"]) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract design guidelines
                        guidelines = soup.find_all(['section', 'div'], class_=['guideline', 'principle'])
                        for guideline in guidelines:
                            title = guideline.find(['h1', 'h2', 'h3'])
                            description = guideline.find('p')
                            if title and description:
                                patterns.append({
                                    "type": "design_guideline",
                                    "title": title.text,
                                    "description": description.text,
                                    "system": source["system_name"]
                                })
            except Exception as e:
                self.log(f"Error extracting from design system: {str(e)}")
        
        return patterns

    def _extract_from_component(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract patterns from component documentation."""
        patterns = []
        
        if source.get("code"):
            patterns.append({
                "type": "component_implementation",
                "name": source["name"],
                "code": source["code"],
                "library": source["library"]
            })
        
        return patterns

    def _extract_from_ux_pattern(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract patterns from UX pattern articles."""
        patterns = []
        
        if source.get("summary"):
            patterns.append({
                "type": "ux_best_practice",
                "title": source["title"],
                "description": source["summary"],
                "source": source["source"]
            })
        
        return patterns

    async def _generate_design(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate UI/UX design based on requirements and learned patterns."""
        component_name = input_data.get("component_name", "Unknown Component")
        
        design = {
            "ui_design": {
                "components": [],
                "layouts": [],
                "interactions": []
            },
            "ux_recommendations": {
                "usability_improvements": [],
                "accessibility_features": []
            }
        }
        
        # Apply learned patterns
        if hasattr(self, "learned_patterns"):
            for pattern_name, pattern in self.learned_patterns.items():
                if self._pattern_matches_requirements(pattern, input_data):
                    if "component" in pattern_name:
                        design["ui_design"]["components"].append(pattern)
                    elif "interaction" in pattern_name:
                        design["ui_design"]["interactions"].append(pattern)
                    elif "usability" in pattern_name:
                        design["ux_recommendations"]["usability_improvements"].append(pattern)
        
        return design

    def _pattern_matches_requirements(self, pattern: str, requirements: Dict[str, Any]) -> bool:
        """Check if a pattern matches design requirements."""
        # TODO: Implement pattern matching logic
        return True 