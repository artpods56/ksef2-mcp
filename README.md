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

## License

---


This software is shared under the [MIT](LICENSE.md) license.

