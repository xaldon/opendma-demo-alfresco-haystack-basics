"""Shared conversion components for fetched Alfresco content."""

from __future__ import annotations

from haystack import Document, component
from haystack.components.converters import HTMLToDocument, PyPDFToDocument, TextFileToDocument
from haystack.components.joiners import DocumentJoiner
from haystack.components.routers import FileTypeRouter
from haystack.dataclasses import ByteStream
from haystack_integrations.components.converters.docling import DoclingConverter

SUPPORTED_MIME_TYPES = [
    "text/plain",
    "text/html",
    "application/pdf",
    "application/msword",
]


@component
class TextDocumentFilter:
    """Drop converted documents without text content."""

    @component.output_types(documents=list[Document])
    def run(self, documents: list[Document]) -> dict[str, list[Document]]:
        return {
            "documents": [
                document
                for document in documents
                if document.content is not None and document.content.strip()
            ]
        }


def add_conversion_components(pipeline: object) -> None:
    """Add common file routing and conversion components to a Haystack pipeline."""
    pipeline.add_component("router", FileTypeRouter(mime_types=SUPPORTED_MIME_TYPES))
    pipeline.add_component("text_converter", TextFileToDocument())
    pipeline.add_component("html_converter", HTMLToDocument())
    pipeline.add_component("pdf_converter", PyPDFToDocument())
    pipeline.add_component("word_converter", DoclingConverter())
    pipeline.add_component("text_filter", TextDocumentFilter())
    pipeline.add_component("joiner", DocumentJoiner())


def connect_conversion_components(pipeline: object, source_socket: str) -> None:
    """Connect a ByteStream source socket to common converters and a document joiner."""
    pipeline.connect(source_socket, "router.sources")
    pipeline.connect("router.text/plain", "text_converter.sources")
    pipeline.connect("router.text/html", "html_converter.sources")
    pipeline.connect("router.application/pdf", "pdf_converter.sources")
    pipeline.connect("router.application/msword", "word_converter.sources")
    pipeline.connect("text_converter.documents", "text_filter.documents")
    pipeline.connect("html_converter.documents", "text_filter.documents")
    pipeline.connect("pdf_converter.documents", "text_filter.documents")
    pipeline.connect("word_converter.documents", "text_filter.documents")
    pipeline.connect("text_filter.documents", "joiner.documents")


def text_extractor(streams: list[ByteStream]) -> list[Document]:
    """Convert text and PDF streams into Haystack Documents for OpenDMA tools."""
    text_streams = [
        stream
        for stream in streams
        if stream.mime_type is not None and stream.mime_type.startswith("text/")
    ]
    pdf_streams = [stream for stream in streams if stream.mime_type == "application/pdf"]

    documents: list[Document] = []
    if text_streams:
        documents.extend(TextFileToDocument().run(sources=text_streams)["documents"])
    if pdf_streams:
        documents.extend(PyPDFToDocument().run(sources=pdf_streams)["documents"])
    return documents

