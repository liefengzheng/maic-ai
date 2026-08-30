# AnyDoc integration research

Research date: 2026-08-30. Sources are limited to the official `firecrawl/anydoc` repository, inspected at commit [`261fc25`](https://github.com/firecrawl/anydoc/commit/261fc257d17c3eab0f673be31c408fd9fdc2171a), including its first-party package and release metadata.

## Executive conclusion

AnyDoc is a fast Rust **library**, not a document server. It converts Word, PowerPoint, Excel, OpenDocument, RTF, EPUB, CSV, and text-based PDF files to GitHub-Flavored Markdown through Rust, Node.js, Python, or browser/WASM bindings. It does not expose an HTTP API or ship a Dockerfile/Compose stack. For this workspace, install the `firecrawl-anydoc` Python wheel in the existing FastAPI image and expose a small, authenticated application-owned upload endpoint. Do not add an AnyDoc service to Compose. Keep optional Firecrawl-hosted OCR disabled unless users explicitly consent to sending the complete PDF off-host. [Repository README](https://github.com/firecrawl/anydoc/blob/main/README.md) · [repository tree](https://github.com/firecrawl/anydoc/tree/main)

## What it does

- Parses `.doc`, `.docx`, `.docm`, `.ppt`, `.pps`, `.pot`, `.pptx`, `.pptm`, `.ppsx`, `.ppsm`, `.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.odt`, `.ods`, `.odp`, `.rtf`, `.epub`, `.csv`, and `.pdf`; output is consistent GFM with document structure, tables, lists, notes, links, and LaTeX equations. [Supported formats and features](https://github.com/firecrawl/anydoc/blob/main/README.md#supported-formats)
- Detects most formats from content rather than trusting the filename. CSV has no signature and needs its extension or an explicit `csv` format. [Format detection](https://github.com/firecrawl/anydoc/blob/main/README.md#format-detection)
- Parses text-based PDFs locally. Image-only/scanned PDF pages produce `NeedsOcrError`; optional `ocr="hosted"` sends the **whole PDF** to Firecrawl Parse because page selection is unavailable. [OCR behavior](https://github.com/firecrawl/anydoc/blob/main/README.md#ocr)
- Embedded binary assets are retained only in the `Document` model; Markdown represents embedded images/objects by alt text. PDF supports Markdown conversion but not the `Document` model. [Python API stubs](https://github.com/firecrawl/anydoc/blob/main/python/anydoc/_anydoc.pyi)

## Local and self-host requirements

### Recommended: released Python wheel

- Package: `firecrawl-anydoc` (import name `anydoc`), currently version `0.2.4` at the inspected commit. It requires Python `>=3.10`; its `abi3-py310` binding covers CPython 3.10 and newer, including this workspace's Python 3.12. [Python package metadata](https://github.com/firecrawl/anydoc/blob/main/python/pyproject.toml) · [PyO3 configuration](https://github.com/firecrawl/anydoc/blob/main/python/Cargo.toml)
- Installation is `pip install firecrawl-anydoc`. The release workflow publishes native wheels for x86_64/aarch64 Linux (manylinux2014/glibc 2.17 and musllinux 1.2), x86_64/aarch64 macOS, and x86_64 Windows. A normal supported deployment needs no Rust compiler. [Release wheel matrix](https://github.com/firecrawl/anydoc/blob/main/.github/workflows/release.yml#L249-L287)
- Local conversion is pure native code: no LibreOffice, Java, ML model, GPU, database, network service, or separate daemon is required. Text PDF support is included through `pdf-inspector`. [Features](https://github.com/firecrawl/anydoc/blob/main/README.md#features) · [Rust dependencies](https://github.com/firecrawl/anydoc/blob/main/Cargo.toml)

### Building from source

Building the Python binding requires Rust `1.88+` (the crate's declared minimum), Python `3.10+`, and `maturin >=1.9,<2`; development uses `maturin develop`. This is unnecessary when a published wheel matches the target. [Cargo metadata](https://github.com/firecrawl/anydoc/blob/main/Cargo.toml) · [Python build system](https://github.com/firecrawl/anydoc/blob/main/python/pyproject.toml) · [development commands](https://github.com/firecrawl/anydoc/blob/main/README.md#development)

### Docker, GPU, and external services

AnyDoc has no official Docker image, Dockerfile, Compose service, HTTP server, or GPU requirement in the repository. The existing `python:3.12-slim` API image can install the manylinux wheel directly. The only optional external dependency is Firecrawl Parse for hosted OCR; it uses `FIRECRAWL_API_KEY` (optional, for higher limits) and `FIRECRAWL_API_URL` (optional override, default `https://api.firecrawl.dev`). [Full repository tree](https://github.com/firecrawl/anydoc/tree/main) · [Python hosted client](https://github.com/firecrawl/anydoc/blob/main/python/anydoc/__init__.py)

## APIs and data formats

### AnyDoc HTTP API

**None.** AnyDoc listens on no port and exposes no HTTP endpoints. Therefore there is no AnyDoc self-host HTTP request/response schema. Its public Python interface is in-process:

| Function                                                                            | Request                                            | Response                                                     |
| ----------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------ |
| `to_markdown(path, *, ocr="reject", api_key=None, api_url=None)`                    | Filesystem path; format detected from content/path | `str` containing GFM                                         |
| `to_markdown_bytes(data, format=None, *, ocr="reject", api_key=None, api_url=None)` | `bytes`/`bytearray`; optional format literal       | `str` containing GFM                                         |
| `to_document(data, format=None)`                                                    | `bytes`/`bytearray`; optional format               | Typed `Document` with `blocks`, `notes`, and binary `assets` |
| `format_from_bytes/extension/path(...)`                                             | Bytes or name/path                                 | Canonical format string or `None`                            |

Conversion failures are typed `ConvertError` subclasses: `UnsupportedError`, `NeedsOcrError` (with 1-based `pages` and `page_count`), `MalformedError`, `EncryptedError`, `ResourceLimitError`, `MissingPartError`, and `HostedError`; unreadable paths raise `OSError`. [Python wrapper](https://github.com/firecrawl/anydoc/blob/main/python/anydoc/__init__.py) · [typed API](https://github.com/firecrawl/anydoc/blob/main/python/anydoc/_anydoc.pyi) · [Python README](https://github.com/firecrawl/anydoc/blob/main/python/README.md)

### Optional Firecrawl Parse call made by AnyDoc

This is a separate hosted service, not an endpoint exposed by AnyDoc:

```http
POST {FIRECRAWL_API_URL-or-https://api.firecrawl.dev}/v2/parse
Content-Type: multipart/form-data; boundary=...
Authorization: Bearer <FIRECRAWL_API_KEY>   # omitted when keyless

options={"parsers":[{"type":"pdf","mode":"auto"}],"origin":"anydoc@<version>"}
file=<complete PDF bytes; Content-Type: application/pdf>
```

The client waits up to 300 seconds. Success must be HTTP 200 with JSON shaped as `{"success": true, "data": {"markdown": "..."}}`; it returns `data.markdown`. Non-200, `success != true`, invalid JSON, or absent/empty Markdown raises `HostedError`. Known statuses are 401 (rejected key), 402 (credits), and 429 (keyed/keyless rate limit). [Exact client implementation](https://github.com/firecrawl/anydoc/blob/main/python/anydoc/__init__.py#L91-L167) · [contract tests](https://github.com/firecrawl/anydoc/blob/main/python/tests/test_anydoc.py#L78-L98)

## Python SDK status

Yes. `firecrawl-anydoc` is an official typed Python binding/SDK around the Rust parser, published to PyPI and imported as `anydoc`. It is not an HTTP client SDK except for the internal hosted-OCR fallback described above. Conversion releases the GIL, allowing other Python threads to run. [Python README](https://github.com/firecrawl/anydoc/blob/main/python/README.md) · [release workflow](https://github.com/firecrawl/anydoc/blob/main/.github/workflows/release.yml)

## License

MIT, copyright 2026 Sideguide Technologies Inc. Use, modification, distribution, sublicensing, and sale are permitted subject to retaining the copyright and permission notice; the software is provided without warranty. [Official license](https://github.com/firecrawl/anydoc/blob/main/LICENSE)

## Security and document privacy

- **Data locality:** default local conversion makes no network call. With hosted OCR, only a document that triggers `NeedsOcrError` is uploaded, but the entire PDF leaves the deployment. Do not enable it silently; apply the external service's data-handling terms separately and avoid it for restricted documents. [OCR behavior](https://github.com/firecrawl/anydoc/blob/main/README.md#ocr)
- **Resource exhaustion:** the parser has fixed, non-configurable caps, including 128 MiB per decompressed archive entry, 512 MiB total decompressed data, 100,000 entries, XML depth 256, 2,000,000 XML nodes per part, 4,000,000 grid/expansion slots, 64 MiB expanded text, 128 MiB retained assets, and bounded legacy-record traversal. Exceeding a cap raises `ResourceLimitError`. These protections do not replace a much smaller HTTP upload limit, request timeout, concurrency limit, or container memory limit. [Exact safety limits](https://github.com/firecrawl/anydoc/blob/main/src/package/limits.rs) · [bounded archive reader](https://github.com/firecrawl/anydoc/blob/main/src/package/archive.rs)
- **Untrusted output:** converted Markdown is attacker-controlled content. Treat it as data, not instructions; never interpolate it into privileged agent/system prompts without clear delimiters and policy controls. Sanitize rendered Markdown/HTML, disable raw HTML, and do not auto-fetch external links/images, which could leak client IP/data or become SSRF if fetched server-side.
- **Retention:** `to_markdown_bytes` avoids temporary files. Do not log document bytes or extracted text; return or persist only what the product requires, with user ownership checks and deletion/retention rules. The richer `Document` object can retain up to 128 MiB of embedded assets in memory, so use Markdown-only conversion unless assets are required. [Document/asset API](https://github.com/firecrawl/anydoc/blob/main/python/anydoc/_anydoc.pyi)

## Recommended workspace architecture

1. Add a pinned `firecrawl-anydoc` dependency to the existing FastAPI project and rebuild the existing API image. Do not add a Compose service, port, volume, GPU reservation, or database solely for AnyDoc.
2. Add an authenticated FastAPI endpoint such as `POST /documents/convert` accepting one `multipart/form-data` file and an explicit `ocr` policy (`reject` by default). Enforce an application upload limit well below parser caps (for example 25 MiB), allowlisted extensions plus content detection, timeout/concurrency controls, and ownership/rate limits. Read bytes and call `anydoc.to_markdown_bytes`; run the synchronous call in Starlette's thread pool so the event loop remains responsive even though the binding releases the GIL.
3. Return an application-owned JSON contract, for example `{"markdown":"...","format":"docx","ocrUsed":false}`, with stable error mappings: unsupported/encrypted/malformed as 422, upload too large as 413, OCR required as 422 with `pages`/`pageCount`, rate limiting as 429, and hosted dependency failure as 502/503. Do not expose raw parser internals or filesystem paths.
4. Have React upload only to FastAPI. Never put a Firecrawl key in browser code. Update nginx to route `/documents`; configure nginx/body-size and FastAPI limits consistently. Keep conversion ephemeral unless the product explicitly needs document storage.
5. If hosted OCR is approved, keep the key server-side, require an explicit user action/notice, restrict `FIRECRAWL_API_URL` to trusted configuration (not request input), record only minimal audit metadata, and budget for the client's 300-second upstream timeout. A private Parse-compatible deployment can be selected through `FIRECRAWL_API_URL`, but AnyDoc's repository does not document or provide that server deployment.

This design keeps credentials, authorization, upload controls, errors, and privacy policy in the existing backend while using AnyDoc in its intended in-process form.
