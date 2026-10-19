"""Pipeline builders and command helpers."""

from __future__ import annotations

from typing import Any

from haystack import Document, Pipeline
from haystack.components.builders import ChatPromptBuilder
from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.writers import DocumentWriter
from haystack.dataclasses import ChatMessage
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.document_stores.types import DuplicatePolicy
from haystack.utils import Secret
from opendma_haystack import AlfrescoFetcher, AlfrescoRetriever, AlfrescoToolset

from opendma_demo_alfresco_haystack_basics.config import Settings
from opendma_demo_alfresco_haystack_basics.conversion import (
    add_conversion_components,
    connect_conversion_components,
    text_extractor,
)


def build_vector_store(settings: Settings, site: str) -> tuple[InMemoryDocumentStore, list[Document]]:
    """Fetch one Alfresco site and index it in an in-memory document store."""
    document_store = InMemoryDocumentStore(embedding_similarity_function="cosine")
    fetcher = AlfrescoFetcher(
        endpoint=settings.endpoint,
        username=settings.username,
        password=settings.password,
        repository_id=settings.repository_id,
    )

    pipeline = Pipeline()
    pipeline.add_component("fetcher", fetcher)
    add_conversion_components(pipeline)
    pipeline.add_component("splitter", DocumentSplitter(split_by="word", split_length=250, split_overlap=40))
    pipeline.add_component(
        "embedder",
        OpenAIDocumentEmbedder(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            model=settings.embedding_model,
        ),
    )
    pipeline.add_component(
        "writer",
        DocumentWriter(document_store=document_store, policy=DuplicatePolicy.OVERWRITE),
    )

    connect_conversion_components(pipeline, "fetcher.streams")
    pipeline.connect("joiner.documents", "splitter.documents")
    pipeline.connect("splitter.documents", "embedder.documents")
    pipeline.connect("embedder.documents", "writer.documents")

    result = pipeline.run(
        {"fetcher": {"sites": [site]}},
        include_outputs_from={"joiner", "splitter"},
    )
    converted = result.get("joiner", {}).get("documents", [])
    return document_store, converted


def ask_vector_store(
    settings: Settings,
    document_store: InMemoryDocumentStore,
    question: str,
    top_k: int,
) -> tuple[str, list[Document]]:
    """Run a simple 2-step RAG query against the in-memory document store."""
    prompt_template = [
        ChatMessage.from_system(
            "You answer questions about information stored in Alfresco. "
            "Use only the provided context. "
            "If the context does not contain the answer, say that you do not know."
        ),
        ChatMessage.from_user(
            """
Question: {{ question }}

Context:
{% for document in documents %}
Title: {{ document.meta.get("opendma:Title", "") }}
Site: {{ document.meta.get("alfresco:Site", "") }}
Path: {{ document.meta.get("alfresco:Path", "") }}
Content:
{{ document.content }}

{% endfor %}
"""
        ),
    ]

    pipeline = Pipeline()
    pipeline.add_component(
        "query_embedder",
        OpenAITextEmbedder(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            model=settings.embedding_model,
        ),
    )
    pipeline.add_component(
        "retriever",
        InMemoryEmbeddingRetriever(document_store=document_store, top_k=top_k),
    )
    pipeline.add_component(
        "prompt_builder",
        ChatPromptBuilder(
            template=prompt_template,
            required_variables={"question", "documents"},
        ),
    )
    pipeline.add_component(
        "llm",
        OpenAIChatGenerator(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            model=settings.chat_model,
            generation_kwargs={"temperature": 0},
        ),
    )

    pipeline.connect("query_embedder.embedding", "retriever.query_embedding")
    pipeline.connect("retriever.documents", "prompt_builder.documents")
    pipeline.connect("prompt_builder.prompt", "llm.messages")

    result = pipeline.run(
        {
            "query_embedder": {"text": question},
            "prompt_builder": {"question": question},
        },
        include_outputs_from={"retriever"},
    )
    documents = result["retriever"]["documents"]
    answer = result["llm"]["replies"][0].text or ""
    return answer, documents


def live_search(settings: Settings, query: str, site: str | None, top_k: int) -> list[Document]:
    """Search Alfresco live and convert matching files into text documents."""
    retriever = AlfrescoRetriever(
        endpoint=settings.endpoint,
        username=settings.username,
        password=settings.password,
        repository_id=settings.repository_id,
        sites=[site] if site else None,
        top_k=top_k,
    )
    fetcher = AlfrescoFetcher(
        endpoint=settings.endpoint,
        username=settings.username,
        password=settings.password,
        repository_id=settings.repository_id,
    )

    pipeline = Pipeline()
    pipeline.add_component("retriever", retriever)
    pipeline.add_component("fetcher", fetcher)
    add_conversion_components(pipeline)
    pipeline.connect("retriever.documents", "fetcher.targets")
    connect_conversion_components(pipeline, "fetcher.streams")

    result = pipeline.run({"retriever": {"query": query}}, include_outputs_from={"retriever"})
    return result.get("joiner", {}).get("documents", [])


def build_agent(settings: Settings) -> Any:
    """Build a Haystack tool-calling agent with AlfrescoToolset."""
    from haystack.components.agents import Agent

    toolset = AlfrescoToolset(
        endpoint=settings.endpoint,
        username=settings.username,
        password=settings.password,
        repository_id=settings.repository_id,
        text_extractor=text_extractor,
    )
    system_prompt = """
You answer questions using documents stored in Alfresco.

Use alfresco_list_sites to discover sites.
Use opendma_search to search for candidate documents.
Use opendma_list_children to inspect folders.
Use opendma_get_metadata before reading a candidate document.
Use opendma_read_text only when the requested information is inside the document.

Do not answer factual repository questions unless the answer is supported by tool results.
"""
    return Agent(
        chat_generator=OpenAIChatGenerator(
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            model=settings.chat_model,
            generation_kwargs={"temperature": 0},
        ),
        tools=toolset,
        system_prompt=system_prompt,
        max_agent_steps=8,
    )
