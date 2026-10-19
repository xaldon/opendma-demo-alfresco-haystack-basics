"""Terminal formatting helpers."""

from __future__ import annotations

import re
from typing import Any

from haystack import Document
from haystack.dataclasses import ChatMessage
from rich.console import Console
from rich.table import Table

console = Console()


def normalize_whitespace(text: str) -> str:
    """Collapse whitespace for compact terminal output."""
    text = text.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def preview_text(text: str | None, limit: int = 800) -> str:
    """Return a compact text preview."""
    normalized = normalize_whitespace(text or "")
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit] + "..."


def document_title(document: Document) -> str:
    """Return a display title from common metadata keys."""
    for key in ("opendma:Title", "opendma:Name", "cm:title", "cm:name", "file_name"):
        value = document.meta.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return document.content or "(untitled)"


def print_document_summary(documents: list[Document], title: str, max_rows: int = 5) -> None:
    """Print a compact table of document metadata."""
    table = Table(title=title)
    table.add_column("Title")
    table.add_column("Site")
    table.add_column("Path")
    table.add_column("OpenDMA ID")

    for document in documents[:max_rows]:
        table.add_row(
            document_title(document),
            str(document.meta.get("alfresco:Site") or ""),
            str(document.meta.get("alfresco:Path") or ""),
            str(document.meta.get("opendma_id") or ""),
        )

    console.print(table)
    if len(documents) > max_rows:
        console.print(f"... {len(documents) - max_rows} more not shown")


def print_metadata_records(documents: list[Document], max_rows: int = 5) -> None:
    """Print first metadata records after indexing/conversion."""
    print_document_summary(documents, "Sample metadata", max_rows=max_rows)


def print_answer(answer: str | None) -> None:
    """Print an answer block."""
    console.print("\n[bold]Answer[/bold]")
    console.print(answer or "")


def print_agent_trace(messages: list[Any]) -> None:
    """Print compact tool calls and tool results from a Haystack agent result."""
    console.print("\n[bold]Tool trace[/bold]")
    for message in messages:
        if not isinstance(message, ChatMessage):
            continue
        if message.tool_calls:
            for tool_call in message.tool_calls:
                console.print(f"[cyan]Tool call[/cyan]: {tool_call.tool_name}")
                console.print(f"Args: {tool_call.arguments}")
        elif message.tool_call_result:
            result_text = preview_text(str(message.tool_call_result.result), limit=1000)
            console.print(f"[green]Tool result[/green]: {result_text}")

