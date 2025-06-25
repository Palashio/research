import os
from langchain_exa import ExaSearchResults
from langchain_tavily import TavilySearch

class SearchProvider:
    def __init__(self, provider="exa"):
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
    
    def search(self, query, num_results=2):
        """
        Perform a search using the configured provider
        Returns results in a consistent format
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
    
    def _convert_tavily_results(self, tavily_results):
        """
        Convert Tavily results to match Exa format for consistency
        """
        class TavilyResultWrapper:
            def __init__(self, tavily_results):
                self.results = []
                if tavily_results and 'results' in tavily_results:
                    for result in tavily_results['results']:
                        self.results.append(TavilyResultItem(result))
        
        class TavilyResultItem:
            def __init__(self, result):
                self.url = result.get('url', '')
                self.title = result.get('title', '')
                self.text = result.get('content', '')
        
        return TavilyResultWrapper(tavily_results)
    
    def get_provider_name(self):
        return self.provider 