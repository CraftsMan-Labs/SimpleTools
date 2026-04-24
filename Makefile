# SimpleTools — local checks and release (uses uv; mirrors .github/workflows/ci.yml + publish).
#
# Typical flow before a release:
#   make ci              # same gates as GitHub CI
#   make publish-dry-run # build + validate upload (no token required for --dry-run)
#   export UV_PUBLISH_TOKEN=...   # PyPI API token (or trusted publishing in CI)
#   make publish         # ci then upload dist/*

UV ?= uv
SOURCES := simpletools tests

.PHONY: help sync lint format typecheck mypy pyright test build clean check ci publish-dry-run publish

help:
	@echo "SimpleTools Makefile (uv)"
	@echo ""
	@echo "  make sync            Install deps (uv sync --all-extras), same as CI"
	@echo "  make lint            Ruff check + format --check"
	@echo "  make format          Apply Ruff formatter"
	@echo "  make typecheck       mypy + pyright"
	@echo "  make test            unittest discover"
	@echo "  make build           Clean dist/ and uv build (sdist + wheel)"
	@echo "  make check           lint + typecheck + test (no sync)"
	@echo "  make ci              sync + check + build (run before publishing)"
	@echo "  make publish-dry-run ci + uv publish --dry-run"
	@echo "  make publish         ci + uv publish (needs UV_PUBLISH_TOKEN)"
	@echo ""

sync:
	$(UV) sync --all-extras

lint:
	$(UV) run ruff check $(SOURCES)
	$(UV) run ruff format $(SOURCES) --check

format:
	$(UV) run ruff format $(SOURCES)

typecheck: mypy pyright

mypy:
	$(UV) run mypy simpletools

pyright:
	$(UV) run pyright

test:
	$(UV) run python -m unittest discover -s tests -v

clean:
	rm -rf dist build *.egg-info .eggs

build: clean
	$(UV) build

check: lint typecheck test

ci: sync check build

publish-dry-run: ci
	$(UV) publish --dry-run

publish: ci
	@test -n "$$UV_PUBLISH_TOKEN" || (echo "error: set UV_PUBLISH_TOKEN for PyPI upload" >&2; exit 1)
	$(UV) publish
