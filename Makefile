UV ?= uv
PORT ?= 8000
HOST ?= 127.0.0.1
PATH_MCP ?= /mcp

.PHONY: setup lint test run-http run-stdio

setup:
	$(UV) venv --python 3.12
	$(UV) sync --extra dev

lint:
	$(UV) run ruff check .

test:
	$(UV) run pytest

run-http:
	$(UV) run python -m mcp_search.app --transport http --host $(HOST) --port $(PORT) --path $(PATH_MCP)

run-stdio:
	$(UV) run python -m mcp_search.app --transport stdio
