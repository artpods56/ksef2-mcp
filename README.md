<div align="center">
<a href="https://github.com/artpods56/ksef2-mcp" title="ksef2-mcp">
  <img src="https://raw.githubusercontent.com/artpods56/ksef2-mcp/master/docs/assets/logo.png" alt="ksef2-mcp logo" width="50%">
</a>

**Python MCP Server for Poland's KSeF (Krajowy System e-Faktur) v2 API built on top of the [ksef2](https://pypi.org/project/ksef2/) SDK.**

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![beartype](https://raw.githubusercontent.com/beartype/beartype-assets/main/badge/bear-ified.svg)](https://github.com/beartype/beartype)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## Instalation

---
Environment can be prepared using [uv](https://github.com/encode/uv) by running:

```bash
uv sync
```

## Usage

---
To run the server, use:
```bash
uv run --env-file .env python -m ksef2_mcp
```

Invoice authoring is exposed as a small stateful runtime, not as one tool per builder method. The intended flow is:

- `create_draft`
- `get_contexts`
- `get_possible_methods`
- `update_draft`
- `build_draft`
- `delete_draft`

## Demo MVP

---
The most realistic MVP scenario currently covered is a standard domestic B2B service invoice:

- Polish seller and buyer
- PLN currency
- standard 23% VAT
- recurring monthly service billing period
- one-off additional service line
- invoice number, issue place, contact data, and line-level supply date

Runnable example:

```bash
uv run python -m ksef2_mcp.demo.standard_service_invoice
```

This writes a realistic FA(3) XML example to `output/standard-service-invoice.xml` through the same draft/context runtime that the MCP server exposes.

## Honest Scope

---
This is suitable for demos and straightforward invoice-generation cases, especially for small businesses issuing simple domestic invoices. It should not yet be presented as full FA(3) coverage for correcting invoices, complex exemption bases, margin procedures, or advanced foreign-currency handling.

## License

---


This software is shared under the [MIT](LICENSE.md) license.
