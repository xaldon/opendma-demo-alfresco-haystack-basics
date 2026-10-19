# Basic Haystack Alfresco OpenDMA Sample

This repository contains small command line applications for the article [Using Alfresco Content in Haystack: Fetching, Live Search,
and Agent Tools with OpenDMA](https://dev.to/stefankopfxaldon/using-alfresco-content-in-haystack-fetching-live-search-and-agent-tools-with-opendma-4anf)

It demonstrates three different integration styles:

- `vector-rag`: fetch Alfresco site content, index it in an in-memory vector store, and answer questions with a simple 2-step RAG loop.
- `live-search`: search Alfresco live through OpenDMA, fetch only matching repository objects, and convert them to text.
- `agent`: give a Haystack agent OpenDMA tools for browsing, searching, inspecting metadata, and reading selected document text.

The examples are intentionally small. They show component behavior and repository context, not a production deployment architecture.

## Prerequisites

You need:

- an existing Alfresco deployment
- an OpenDMA REST endpoint for Alfresco
- an OpenAI API key for `vector-rag` and `agent`

The examples assume the OpenDMA endpoint is available at:

```text
http://localhost:7070/opendma/alf
```

You can override this and other settings with environment variables.

## Running an OpenDMA Endpoint for Alfresco

The quickest way to map Alfresco to the OpenDMA data model and expose an OpenDMA
REST endpoint is to run the [ECI Server](https://github.com/xaldon/eci-server).
It is available free of charge for non-production use.

Start it with Docker Compose:

```bash
git clone https://github.com/xaldon/eci-server.git
cd eci-server/docker_compose
docker compose up -d
```

After the service is running:

1. Open the web UI at `http://localhost:7070`.
2. Initialize the admin account.
3. Accept the license agreement.
4. Install a free-of-charge license key.
5. Navigate to "Admin" > "Connections".
6. Add a new connection to `Alfresco Content Services`.
7. Choose "Automatically detect parameters with Smart Setup" for target server `host.docker.internal`.
8. Save the new connection as `Alfresco @ host.docker.internal`.
9. Navigate to "Admin" > "REST Endpoints".
10. Add a new REST Endpoint.
11. Set the slug to `opendma/alf`.
12. Select the `Alfresco @ host.docker.internal` connection.
13. Keep the proposed "Inbound Authentication" ("HTTP Basic" and "Propagate Inbound").
14. Save the new REST Endpoint

The example expects the OpenDMA endpoint at:

```text
http://localhost:7070/opendma/alf
```

To verify this REST endpoint, you can open `http://localhost:7070/opendma/alf/` (with a trailing slash)
in a web browser and authenticate with your Alfresco credentials (`admin/admin` by default).

## Configuration

The examples use these environment variables:

```text
OPENDMA_ALFRESCO_ENDPOINT=http://localhost:7070/opendma/alf
ALFRESCO_USERNAME=admin
ALFRESCO_PASSWORD=admin
ALFRESCO_REPOSITORY_ID=Alfresco
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

The `admin/admin` defaults are only for a local tutorial setup. In production, call the OpenDMA endpoint with the effective user's identity when permissions and security markings matter.

## Install

From this directory:

```bash
uv sync
```

## Vector RAG

Fetch one Alfresco site, index it in an in-memory document store, and start an interactive question loop:

```bash
uv run alfresco-haystack-demo vector-rag swsdp
```

Answer one question and exit:

```bash
uv run alfresco-haystack-demo vector-rag swsdp --question "Who attended the January 2011 meeting?"
```

Low-level pypdf parser warnings are hidden by default. Add `--verbose` to any command to show
them while troubleshooting:

```bash
uv run alfresco-haystack-demo vector-rag swsdp --verbose
```

## Live Search

Search Alfresco live and fetch only matching content:

```bash
uv run alfresco-haystack-demo live-search "meeting notes" --site swsdp
```

If `--site` is omitted, the command searches across the entire repository exposed by the OpenDMA endpoint:

```bash
uv run alfresco-haystack-demo live-search "meeting notes"
```

This is Alfresco full-text search, not semantic vector search. Search terms matter.

## Agent Tools

Start an interactive tool-calling agent:

```bash
uv run alfresco-haystack-demo agent
```

Answer one question and exit:

```bash
uv run alfresco-haystack-demo agent --question "Where can I find the meeting notes of the web site design project?"
```

Print compact tool-call information:

```bash
uv run alfresco-haystack-demo agent --question "What is the state of localisation of our new website design?" --trace
```

The agent can list Alfresco sites, search, list folder children, inspect metadata, describe classes, and read selected text chunks.

## Further reading:

- [Using Alfresco Content in Haystack: Fetching, Live Search, and Agent Tools with OpenDMA](https://dev.to/stefankopfxaldon/using-alfresco-content-in-haystack-fetching-live-search-and-agent-tools-with-opendma-4anf)
- OpenDMA: https://opendma.org/
- ECI Server: https://xaldon.com/products/eci-server
- OpenDMA Haystack integration: https://github.com/OpenDMA/opendma-haystack
- Tutorials: https://github.com/OpenDMA/opendma-haystack/tree/main/docs/tutorials
- Fetcher documentation: https://github.com/OpenDMA/opendma-haystack/blob/main/docs/Fetcher.md
- Retriever documentation: https://github.com/OpenDMA/opendma-haystack/blob/main/docs/Retriever.md
- Toolset documentation: https://github.com/OpenDMA/opendma-haystack/blob/main/docs/Toolset.md
