from .base_web_search import BaseWebSearch
from google.genai import types
from tavily import TavilyClient
from typing import Literal


class TavilySearch(BaseWebSearch):
    """A class to perform Tavily search with content summarization."""

    def __init__(
        self,
        api_key: str,
        summarize_model: str,
        **kwargs,
    ):
        """Initialize TavilySearch with API key.

        Args:
            api_key: Tavily API key. If None, uses TAVILY_API_KEY from environment.
            summarize_model: Model to use for summarization. If None, uses GEMINI_MODEL from environment.
            vertexai: Whether to use Vertex AI. If None, uses GOOGLE_GENAI_USE_VERTEXAI from environment.
            vertexai_project: Vertex AI project. If None, uses GOOGLE_CLOUD_PROJECT from environment.
            vertexai_location: Vertex AI location. If None, uses GOOGLE_CLOUD_LOCATION from environment.
            google_ai_studio_api_key: Google AI Studio API key. If None, uses GOOGLE_AI_STUDIO_API_KEY from environment.
            **kwargs: Additional keyword arguments to summarize model config.
        """
        if not api_key or not summarize_model:
            raise ValueError("api_key and summarize_model must be provided")
        self.api_key = api_key
        self.tavily_client = TavilyClient(api_key=self.api_key)
        super().__init__(
            summarize_model=summarize_model,
            **kwargs,
        )

    def _search_multiple(
        self,
        search_queries: list[str],
        max_results: int = 3,
        topic: Literal["general", "news", "finance"] = "general",
        include_raw_content: bool = True,
    ) -> list[dict]:
        """Perform search using Tavily API for multiple queries.

        Args:
            search_queries: List of search queries to execute
            max_results: Maximum number of results per query
            topic: Topic filter for search results
            include_raw_content: Whether to include raw webpage content

        Returns:
            List of search result dictionaries
        """
        search_docs = []
        for query in search_queries:
            result = self.tavily_client.search(
                query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic,
            )
            search_docs.append(result)

        return search_docs

    def _deduplicate_search_results(self, search_results: list[dict]) -> dict:
        """Deduplicate search results by URL to avoid processing duplicate content.

        Args:
            search_results: List of search result dictionaries

        Returns:
            Dictionary mapping URLs to unique results
        """
        unique_results = {}

        for response in search_results:
            for result in response["results"]:
                url = result["url"]
                if url not in unique_results:
                    unique_results[url] = result

        return unique_results

    def _process_search_results(self, unique_results: dict) -> dict:
        """Process search results by summarizing content where available.

        Args:
            unique_results: Dictionary of unique search results

        Returns:
            Dictionary of processed results with summaries
        """
        summarized_results = {}

        for url, result in unique_results.items():
            if not result.get("raw_content"):
                content = result["content"]
            else:
                content = self._summarize_web_content(result["raw_content"])

            summarized_results[url] = {"title": result["title"], "content": content}

        return summarized_results

    def _format_output(self, summarized_results: dict) -> str:
        """Format search results for output.

        Args:
            summarized_results: Dictionary of processed results

        Returns:
            Formatted string of search results
        """
        if not summarized_results:
            return "No results or findings."
        formatted_output = "Search results: \n\n"
        for i, (url, result) in enumerate(summarized_results.items(), 1):
            formatted_output += f"\n\n--- SOURCE {i}: {result['title']} ---\n"
            formatted_output += f"URL: {url}\n\n"
            formatted_output += (
                f"\n{result['content']}\n\n"
                if result.get("content", "").strip()
                else ""
            )
            formatted_output += "-" * 10 + "\n"
        return formatted_output

    def __call__(
        self,
        query: str,
        max_results: int = 3,
        topic: Literal["general", "news", "finance"] = "general",
        **kwargs,
    ) -> str:
        """Fetch results from Tavily search API with content summarization.

        Args:
            query: A single search query to execute
            max_results: Maximum number of results to return
            topic: Topic to filter results by ('general', 'news', 'finance')
            **kwargs: Override summarize model config fields.

        Returns:
            Formatted string of search results with summaries
        """
        if kwargs:
            self.summarize_model_config = types.GenerateContentConfig(
                **{
                    **self.summarize_model_config.model_dump(exclude_none=True),
                    **kwargs,
                }
            )
        search_results = self._search_multiple(
            [query],
            max_results=max_results,
            topic=topic,
            include_raw_content=True,
        )
        unique_results = self._deduplicate_search_results(search_results)
        summarized_results = self._process_search_results(unique_results)

        return self._format_output(summarized_results)
