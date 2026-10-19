"""Command line interface for the sample applications."""

from __future__ import annotations

import logging
from collections.abc import Callable

import typer
from haystack.dataclasses import ChatMessage

from opendma_demo_alfresco_haystack_basics.config import load_settings, require_openai_api_key
from opendma_demo_alfresco_haystack_basics.formatting import (
    console,
    preview_text,
    print_agent_trace,
    print_answer,
    print_document_summary,
    print_metadata_records,
)
from opendma_demo_alfresco_haystack_basics.pipelines import (
    ask_vector_store,
    build_agent,
    build_vector_store,
    live_search,
)

app = typer.Typer(help="Sample Haystack applications for Alfresco content through OpenDMA.")


def _configure_library_logging(verbose: bool) -> None:
    """Hide recoverable PDF parsing warnings unless verbose output is requested."""
    logging.getLogger("pypdf").setLevel(logging.WARNING if verbose else logging.ERROR)


def _question_loop(callback: Callable[[str], None]) -> None:
    """Run a small question loop for interactive commands."""
    while True:
        question = typer.prompt("Question", default="", show_default=False).strip()
        if question.lower() in {"exit", "quit"}:
            return
        if not question:
            console.print('Type "exit" or "quit" to end the application.')
            continue
        callback(question)


@app.command("vector-rag")
def vector_rag(
    site: str = typer.Argument(..., help="Alfresco site short name to index."),
    question: str | None = typer.Option(None, "--question", "-q", help="Ask one question and exit."),
    top_k: int = typer.Option(6, "--top-k", help="Number of chunks to retrieve for each question."),
    verbose: bool = typer.Option(False, "--verbose", help="Show dependency warnings."),
) -> None:
    """Fetch one Alfresco site, index it, and answer questions from the vector store."""
    _configure_library_logging(verbose)
    require_openai_api_key()
    settings = load_settings()

    console.print(f"Indexing Alfresco site [bold]{site}[/bold] from {settings.endpoint}")
    document_store, converted_documents = build_vector_store(settings, site)
    console.print(f"Converted documents: {len(converted_documents)}")
    console.print(f"Indexed chunks: {document_store.count_documents()}")
    print_metadata_records(converted_documents)

    def answer(current_question: str) -> None:
        response, retrieved = ask_vector_store(settings, document_store, current_question, top_k)
        console.print(f"\nRetrieved chunks: {len(retrieved)}")
        print_document_summary(retrieved, "Top retrieved chunks", max_rows=3)
        print_answer(response)

    if question:
        answer(question)
        return

    console.print('\nAsk questions about the indexed site. Type "exit" or "quit" to end.')
    _question_loop(answer)


@app.command("live-search")
def live_search_command(
    query: str = typer.Argument(..., help="Full-text search query."),
    site: str | None = typer.Option(None, "--site", help="Optional Alfresco site short name."),
    top_k: int = typer.Option(8, "--top-k", help="Maximum repository search hits."),
    verbose: bool = typer.Option(False, "--verbose", help="Show dependency warnings."),
) -> None:
    """Search Alfresco live, fetch matching documents, and print compact previews."""
    _configure_library_logging(verbose)
    settings = load_settings()
    scope = f"site {site}" if site else "entire repository"
    console.print(f"Searching {scope}: [bold]{query}[/bold]")

    documents = live_search(settings, query, site, top_k)
    console.print(f"Converted matching documents: {len(documents)}")
    print_document_summary(documents, "Matching documents", max_rows=10)

    for index, document in enumerate(documents[:5], start=1):
        console.print(f"\n[bold]Result {index}[/bold]")
        console.print(f"Title: {document.meta.get('opendma:Title')}")
        console.print(f"Site: {document.meta.get('alfresco:Site')}")
        console.print(f"Path: {document.meta.get('alfresco:Path')}")
        console.print(f"OpenDMA ID: {document.meta.get('opendma_id')}")
        console.print(preview_text(document.content, limit=800))


@app.command("agent")
def agent_command(
    question: str | None = typer.Option(None, "--question", "-q", help="Ask one question and exit."),
    trace: bool = typer.Option(False, "--trace", help="Print compact tool-call trace."),
    verbose: bool = typer.Option(False, "--verbose", help="Show dependency warnings."),
) -> None:
    """Start an Alfresco repository agent backed by OpenDMA tools."""
    _configure_library_logging(verbose)
    require_openai_api_key()
    settings = load_settings()
    agent = build_agent(settings)

    def answer(current_question: str) -> None:
        result = agent.run(messages=[ChatMessage.from_user(current_question)])
        last_message = result.get("last_message")
        if isinstance(last_message, ChatMessage):
            print_answer(last_message.text)
        else:
            print_answer(str(last_message))
        if trace:
            messages = result.get("messages", [])
            if isinstance(messages, list):
                print_agent_trace(messages)

    if question:
        answer(question)
        return

    console.print('Ask questions using Alfresco repository tools. Type "exit" or "quit" to end.')
    _question_loop(answer)


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
