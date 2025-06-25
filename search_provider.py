"""
Search Provider Module

This module provides a unified interface for different search providers (Exa, Tavily)
to abstract away the differences in their APIs and provide consistent search results.
"""

import os
from typing import List, Dict, Any, Optional
from langchain_exa import ExaSearchResults
from langchain_tavily import TavilySearch


class SearchProvider:
    """
    A unified search provider that abstracts different search APIs.
    
    This class provides a consistent interface for searching across different
    providers like Exa and Tavily, handling their specific APIs and result formats.
    """
    
    def __init__(self, provider: str = "exa"):
        """
        Initialize the search provider.
        
        Args:
            provider: The search provider to use ("exa" or "tavily")
            
        Raises:
            ValueError: If the provider is not supported or API key is missing
        """
        self.provider = provider
        if provider == "exa":
            if not os.environ.get("EXA_API_KEY"):
                raise ValueError("EXA_API_KEY environment variable is required for Exa search")
            self.search_tool = ExaSearchResults(exa_api_key=os.environ["EXA_API_KEY"])
        elif provider == "tavily":
            if not os.environ.get("TAVILY_API_KEY"):
                raise ValueError("TAVILY_API_KEY environment variable is required for Tavily search")
            self.search_tool = TavilySearch(
                max_results=2,
                topic="general",
            )
        else:
            raise ValueError(f"Unsupported search provider: {provider}")
    
    def search(self, query: str, num_results: int = 2) -> Any:
        """
        Perform a search using the configured provider.
        
        Args:
            query: The search query string
            num_results: Number of results to return (default: 2)
            
        Returns:
            Search results in a consistent format, or None if search fails
            
        Raises:
            Exception: If the search fails or provider is not configured
        """
        try:
            if self.provider == "exa":
                results = self.search_tool._run(
                    query=query,
                    num_results=2,
                    text_contents_options={"max_characters": 30000},
                    livecrawl="never",
                )
                return results
            elif self.provider == "tavily":
                results = self.search_tool.invoke(query)
                # Convert Tavily results to match Exa format
                return self._convert_tavily_results(results)
        except Exception as e:
            print(f"Search error on '{query}' with {self.provider}: {e}")
            return None
    
    def _convert_tavily_results(self, tavily_results: Dict[str, Any]) -> Any:
        """
        Convert Tavily results to match Exa format for consistency.
        
        Args:
            tavily_results: Raw results from Tavily search API
            
        Returns:
            Wrapper object with results in Exa-compatible format
        """
        class TavilyResultWrapper:
            """Wrapper class to provide Exa-compatible result format for Tavily results."""
            def __init__(self, tavily_results: Dict[str, Any]):
                self.results = []
                if tavily_results and 'results' in tavily_results:
                    for result in tavily_results['results']:
                        self.results.append(TavilyResultItem(result))
        
        class TavilyResultItem:
            """Individual result item wrapper for Tavily results."""
            def __init__(self, result: Dict[str, Any]):
                self.url = result.get('url', '')
                self.title = result.get('title', '')
                self.text = result.get('content', '')
        
        return TavilyResultWrapper(tavily_results)
    
    def get_provider_name(self) -> str:
        """
        Get the name of the current search provider.
        
        Returns:
            Name of the configured search provider
        """
        return self.provider 