from dataclasses import dataclass, field
from google.genai import types
from .base_web_search import BaseWebSearch


@dataclass
class GoogleGrounding:
    title: str = ""
    url: str = ""


@dataclass
class GoogleGroundings:
    summary: str = ""
    grounding_list: list[GoogleGrounding] = field(default_factory=list)


class GoogleSearch(BaseWebSearch):
    """A class to perform Tavily search with content summarization."""

    def __init__(
        self,
        search_model: str,
        summarize_model: str,
        **kwargs,
    ):
        if not search_model:
            raise ValueError("search_model must be provided")
        self.search_model = search_model

        super().__init__(
            summarize_model=summarize_model,
            **kwargs.get("summarize_model_config", dict()),
        )

        search_model_config = kwargs.get("search_model_config", dict())
        self.search_genai_client = self._create_genai_client(
            search_model, search_model_config
        )
        self.search_model_config = types.GenerateContentConfig(
            **{
                **{
                    "tools": [types.Tool(google_search=types.GoogleSearch())],
                    "response_modalities": ["TEXT"],
                },
                **{
                    k: v
                    for k, v in search_model_config.items()
                    if k in ["temperature", "top_p", "top_k", "max_output_tokens"]
                },
            },
        )

        self.groundings = GoogleGroundings()

    def __call__(self, query: str, **kwargs) -> str:
        if kwargs:
            if "search_model_config" in kwargs:
                self.search_model_config = types.GenerateContentConfig(
                    **{
                        **self.search_model_config.model_dump(exclude_none=True),
                        **kwargs["search_model_config"],
                    }
                )
            if "summarize_model_config" in kwargs:
                self.summarize_model_config = types.GenerateContentConfig(
                    **{
                        **self.summarize_model_config.model_dump(exclude_none=True),
                        **kwargs["summarize_model_config"],
                    }
                )

        response = self.search_genai_client.models.generate_content(
            model=self.search_model, contents=query, config=self.search_model_config
        )

        texts = ""
        for candidate in response.candidates:
            grounding = GoogleGrounding()

            content = candidate.content
            if content:
                if content.parts:
                    for part in content.parts:
                        texts += part.text if part.text else ""
                        texts += "\n"

            grounding_metadata = candidate.grounding_metadata
            if grounding_metadata:
                if grounding_metadata.grounding_chunks:
                    for chunk in grounding_metadata.grounding_chunks:
                        if chunk.web:
                            grounding.title = chunk.web.title if chunk.web.title else ""
                            grounding.url = chunk.web.uri if chunk.web.uri else ""
                            # check if url is already in grounding_list
                            if grounding.url not in [
                                g.url for g in self.groundings.grounding_list
                            ]:
                                self.groundings.grounding_list.append(grounding)

        if texts.strip() == "":
            return "No results and findings."

        summary = self._summarize_web_content(texts)
        self.groundings.summary = summary

        formatted_output = "\n" + "---" * 10 + " SOURCES " + "---" * 10 + "\n\n"
        if self.groundings.summary.strip():
            formatted_output += "---" * 10 + " SUMMARY " + "---" * 10 + "\n"
            formatted_output += f"{self.groundings.summary}\n"
            formatted_output += "---" * 10 + " END OF SUMMARY " + "---" * 10 + "\n"
        for i, google_grounding in enumerate(self.groundings.grounding_list):
            formatted_output += f"--- SOURCE {i}: {google_grounding.title} ---\n"
            formatted_output += f"URL: {google_grounding.url}\n"
        formatted_output += "\n" + "---" * 10 + " END OF SOURCES " + "---" * 10 + "\n"

        # logger.debug(formatted_output)
        return formatted_output
