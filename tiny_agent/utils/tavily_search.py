import os
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from tavily import TavilyClient


class Summary(BaseModel):
    """Schema for webpage content summarization."""

    summary: str = Field(description="Concise summary of the webpage content")
    key_excerpts: str = Field(
        description="Important quotes and excerpts from the content"
    )


class TavilySearch:
    """A class to perform Tavily search with content summarization."""

    def __init__(
        self,
        api_key: str = None,
        summarize_model: str = None,
        vertexai: bool = True,
        vertexai_project: str = None,
        vertexai_location: str = None,
        google_ai_studio_api_key=None,
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
            **kwargs: Additional keyword arguments to model config.
        """
        if not api_key or not summarize_model:
            raise ValueError("api_key and summarize_model must be provided")
        self.api_key = api_key
        self.summarize_model = summarize_model

        if vertexai and not (vertexai_project and vertexai_location):
            raise ValueError(
                "vertexai_project and vertexai_location must be provided when vertexai is True"
            )
        if not vertexai and not google_ai_studio_api_key:
            raise ValueError(
                "google_ai_studio_api_key must be provided when vertexai is False"
            )
        self.vertexai = vertexai
        self.vertexai_project = vertexai_project
        self.vertexai_location = vertexai_location
        self.google_ai_studio_api_key = google_ai_studio_api_key

        self.tavily_client = TavilyClient(api_key=self.api_key)
        self.genai_client = genai.Client(
            **(
                {
                    "vertexai": self.vertexai,
                    "project": self.vertexai_project,
                    "location": (
                        "global"
                        if "-preview" in self.summarize_model
                        else self.vertexai_location
                    ),
                }
                if self.vertexai
                else {
                    "api_key": self.google_ai_studio_api_key,
                }
            ),
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=3),
            ),
        )
        self.config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Summary,
            **kwargs,
        )

    def _summarize_web_content(self, webpage_content: str) -> str:
        """Summarize webpage content using the configured summarization model.

        Args:
            webpage_content: Raw webpage content to summarize

        Returns:
            Formatted summary with key excerpts
        """
        try:
            prompt = """You are tasked with summarizing the raw content of a webpage retrieved from a web search. Your goal is to create a summary that preserves the most important information from the original web page. This summary will be used by a downstream research agent, so it's crucial to maintain the key details without losing essential information.

Here is the raw content of the webpage:

<webpage_content>
{webpage_content}
</webpage_content>

Please follow these guidelines to create your summary:

1. Identify and preserve the main topic or purpose of the webpage.
2. Retain key facts, statistics, and data points that are central to the content's message.
3. Keep important quotes from credible sources or experts.
4. Maintain the chronological order of events if the content is time-sensitive or historical.
5. Preserve any lists or step-by-step instructions if present.
6. Include relevant dates, names, and locations that are crucial to understanding the content.
7. Summarize lengthy explanations while keeping the core message intact.

When handling different types of content:

- For news articles: Focus on the who, what, when, where, why, and how.
- For scientific content: Preserve methodology, results, and conclusions.
- For opinion pieces: Maintain the main arguments and supporting points.
- For product pages: Keep key features, specifications, and unique selling points.

Your summary should be significantly shorter than the original content but comprehensive enough to stand alone as a source of information. Aim for about 25-30 percent of the original length, unless the content is already concise.

Present your summary in the following format:

```
{{
   "summary": "Your summary here, structured with appropriate paragraphs or bullet points as needed",
   "key_excerpts": "First important quote or excerpt, Second important quote or excerpt, Third important quote or excerpt, ...Add more excerpts as needed, up to a maximum of 5"
}}
```

Here are two examples of good summaries:

Example 1 (for a news article):
```json
{{
   "summary": "On July 15, 2023, NASA successfully launched the Artemis II mission from Kennedy Space Center. This marks the first crewed mission to the Moon since Apollo 17 in 1972. The four-person crew, led by Commander Jane Smith, will orbit the Moon for 10 days before returning to Earth. This mission is a crucial step in NASA's plans to establish a permanent human presence on the Moon by 2030.",
   "key_excerpts": "Artemis II represents a new era in space exploration, said NASA Administrator John Doe. The mission will test critical systems for future long-duration stays on the Moon, explained Lead Engineer Sarah Johnson. We're not just going back to the Moon, we're going forward to the Moon, Commander Jane Smith stated during the pre-launch press conference."
}}
```

Example 2 (for a scientific article):
```json
{{
   "summary": "A new study published in Nature Climate Change reveals that global sea levels are rising faster than previously thought. Researchers analyzed satellite data from 1993 to 2022 and found that the rate of sea-level rise has accelerated by 0.08 mm/year² over the past three decades. This acceleration is primarily attributed to melting ice sheets in Greenland and Antarctica. The study projects that if current trends continue, global sea levels could rise by up to 2 meters by 2100, posing significant risks to coastal communities worldwide.",
   "key_excerpts": "Our findings indicate a clear acceleration in sea-level rise, which has significant implications for coastal planning and adaptation strategies, lead author Dr. Emily Brown stated. The rate of ice sheet melt in Greenland and Antarctica has tripled since the 1990s, the study reports. Without immediate and substantial reductions in greenhouse gas emissions, we are looking at potentially catastrophic sea-level rise by the end of this century, warned co-author Professor Michael Green."  
}}
```

Remember, your goal is to create a summary that can be easily understood and utilized by a downstream research agent while preserving the most critical information from the original webpage."""

            response = self.genai_client.models.generate_content(
                model=self.summarize_model,
                contents=prompt.format(webpage_content=webpage_content),
                config=self.config,
            )
            summary = response.parsed
            formatted_summary = (
                f"SUMMARY:\n{summary.summary}\n\nKEY EXCERPTS:\n{summary.key_excerpts}"
            )

            return formatted_summary

        except Exception as e:
            print(f"Failed to summarize webpage: {str(e)}")
            return (
                webpage_content[:1000] + "..."
                if len(webpage_content) > 1000
                else webpage_content
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
            formatted_output += f"SUMMARY:\n{result['content']}\n\n"
            formatted_output += "-" * 80 + "\n"
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
            **kwargs: A dict try to override the current model config.

        Returns:
            Formatted string of search results with summaries
        """
        if kwargs:
            self.config = {**self.config, **kwargs}
        search_results = self._search_multiple(
            [query],
            max_results=max_results,
            topic=topic,
            include_raw_content=True,
        )
        unique_results = self._deduplicate_search_results(search_results)
        summarized_results = self._process_search_results(unique_results)

        return self._format_output(summarized_results)
