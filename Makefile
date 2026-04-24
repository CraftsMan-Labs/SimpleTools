# simpleAgentTools — tests, preflight, semver bumps, PyPI publish (uv).
#
# Typical release (after changes are committed):
#   make test              # run unit tests
#   make preflight         # sync + lint + types + tests + build + uv publish --dry-run
#   make version-patch     # bump pyproject version, uv lock, commit, tag vX.Y.Z, push
#   make publish-doppler   # preflight + uv publish inside doppler run (see Doppler notes below)
#
# Doppler: pick one — (1) run `doppler setup` in this repo, (2) export DOPPLER_PROJECT + DOPPLER_CONFIG,
# (3) make publish-doppler DOPPLER_OPTS='--project YOUR_PROJECT --config dev'

UV ?= uv
SOURCES := simpletools tests
PYPROJECT ?= pyproject.toml
LOCKFILE ?= uv.lock
GIT_REMOTE ?= origin
DOPPLER ?= doppler
# Extra args for `doppler run`, e.g. --project my-app --config dev (or -p / -c shorthand)
DOPPLER_OPTS ?=

.PHONY: help sync lint format typecheck mypy pyright test build clean check ci \
	preflight check-publish publish-dry-only publish-dry-run publish-doppler \
	_publish-uv-do _publish-doppler-seq \
	version-get version-next-patch version-next-minor version-next-major \
	version-patch version-minor version-major version-set tag-release

help:
	@echo "simpleAgentTools — common commands"
	@echo ""
	@echo "  make test              Run unit tests (unittest)"
	@echo "  make preflight         Pre-publish gate: sync, lint, types, tests, build, uv publish --dry-run"
	@echo "  make publish-doppler   Preflight + publish entirely inside Doppler (token never needed in shell; avoids uv username/password prompts)"
	@echo ""
	@echo "Version (pyproject.toml + $(LOCKFILE), then git commit, tag, push):"
	@echo "  make version-get             Show current version"
	@echo "  make version-patch           Bump patch (0.1.0 -> 0.1.1)"
	@echo "  make version-minor           Bump minor (0.1.0 -> 0.2.0)"
	@echo "  make version-major           Bump major (0.1.0 -> 1.0.0)"
	@echo "  make version-set VERSION=X   Set exact version"
	@echo "  make tag-release             Tag vX.Y.Z from current pyproject + push (also runs after each version-* above)"
	@echo ""
	@echo "Granular (same as before):"
	@echo "  make sync / lint / format / typecheck / build / check / ci"
	@echo "  make publish-dry-run       Alias: same as preflight"
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

# Pre-publish: everything CI does, plus validate PyPI metadata via dry-run.
preflight:
	@echo "==> Preflight (sync, checks, build, publish dry-run)..."
	@$(MAKE) sync
	@$(MAKE) check
	@$(MAKE) build
	@set -e; \
	token="$${PYPI_TOKEN:-$${UV_PUBLISH_TOKEN:-$${V_PUBLISH_TOKEN}}}"; \
	if [ -n "$$token" ]; then \
		$(UV) publish --dry-run --token "$$token"; \
	else \
		$(UV) publish --dry-run; \
	fi
	@echo "==> Preflight passed."

check-publish: preflight

publish-dry-only:
	$(UV) publish --dry-run

publish-dry-run: preflight

# Prefer PYPI_TOKEN; also accept UV_PUBLISH_TOKEN (uv) and V_PUBLISH_TOKEN (SimpleAgents publish-python).
_publish-uv-do:
	@set -e; \
	token="$${PYPI_TOKEN:-$${UV_PUBLISH_TOKEN:-$${V_PUBLISH_TOKEN}}}"; \
	if [ -z "$$token" ]; then \
		echo "error: missing PyPI token." >&2; \
		echo "  Store PYPI_TOKEN (or UV_PUBLISH_TOKEN / V_PUBLISH_TOKEN) in Doppler and run make publish-doppler." >&2; \
		exit 1; \
	fi; \
	UV_PUBLISH_TOKEN=$$token $(UV) publish --token "$$token"

# Run preflight + upload inside Doppler so dry-run and publish both see PYPI_TOKEN (etc.).
publish-doppler:
	@$(DOPPLER) run $(DOPPLER_OPTS) --command "cd $(CURDIR) && $(MAKE) --no-print-directory _publish-doppler-seq"

_publish-doppler-seq: preflight
	@$(MAKE) --no-print-directory _publish-uv-do

# --- version (pyproject.toml semver) ----------------------------------------

version-get:
	@grep '^version = ' "$(PYPROJECT)" | head -1 | sed 's/version = "\(.*\)"/\1/'

version-next-patch:
	@current=$$($(MAKE) --no-print-directory version-get); \
	IFS='.' read -r major minor patch <<< "$$current"; \
	patch=$$((patch + 1)); \
	echo "$$major.$$minor.$$patch"

version-next-minor:
	@current=$$($(MAKE) --no-print-directory version-get); \
	IFS='.' read -r major minor patch <<< "$$current"; \
	minor=$$((minor + 1)); \
	echo "$$major.$$minor.0"

version-next-major:
	@current=$$($(MAKE) --no-print-directory version-get); \
	IFS='.' read -r major minor patch <<< "$$current"; \
	major=$$((major + 1)); \
	echo "$$major.0.0"

define bump_version
	@case " $(MAKEFLAGS) " in *" -n "*|*" --just-print "*|*" --dry-run "*); \
		echo "Error: $(1) cannot run with -n/--just-print/--dry-run"; \
		exit 1; \
	esac; \
	set -euo pipefail; \
	current=$$(grep '^version = ' "$(PYPROJECT)" | head -1 | sed 's/version = "\(.*\)"/\1/'); \
	$(2); \
	echo "Bumping version: $$current -> $$new"; \
	sed -i.bak 's/^version = ".*"/version = "'$$new'"/' "$(PYPROJECT)"; \
	rm -f "$(PYPROJECT).bak"; \
	$(UV) lock; \
	git add "$(PYPROJECT)" "$(LOCKFILE)"; \
	git commit -m "chore(release): bump version to $$new"; \
	$(MAKE) --no-print-directory tag-release; \
	echo "Version bumped, committed, tagged, and pushed: $$new"
endef

version-patch:
	$(call bump_version,version-patch,\
	IFS='.' read -r major minor patch <<< "$$current"; \
	patch=$$((patch + 1)); \
	new="$$major.$$minor.$$patch")

version-minor:
	$(call bump_version,version-minor,\
	IFS='.' read -r major minor patch <<< "$$current"; \
	minor=$$((minor + 1)); \
	new="$$major.$$minor.0")

version-major:
	$(call bump_version,version-major,\
	IFS='.' read -r major minor patch <<< "$$current"; \
	major=$$((major + 1)); \
	new="$$major.0.0")

version-set:
	@case " $(MAKEFLAGS) " in *" -n "*|*" --just-print "*|*" --dry-run "*); \
		echo "Error: version-set cannot run with -n/--just-print/--dry-run"; \
		exit 1; \
	esac; \
	set -euo pipefail; \
	if [ -z "$(VERSION)" ]; then \
		echo "Usage: make version-set VERSION=0.2.0" >&2; \
		exit 1; \
	fi; \
	current=$$(grep '^version = ' "$(PYPROJECT)" | head -1 | sed 's/version = "\(.*\)"/\1/'); \
	echo "Setting version: $$current -> $(VERSION)"; \
	sed -i.bak 's/^version = ".*"/version = "$(VERSION)"/' "$(PYPROJECT)"; \
	rm -f "$(PYPROJECT).bak"; \
	$(UV) lock; \
	git add "$(PYPROJECT)" "$(LOCKFILE)"; \
	git commit -m "chore(release): bump version to $(VERSION)"; \
	$(MAKE) --no-print-directory tag-release; \
	echo "Version set, committed, tagged, and pushed: $(VERSION)"

tag-release:
	@version=$$($(MAKE) --no-print-directory version-get); \
	echo "Creating tag v$$version..."; \
	git tag -a "v$$version" -m "Release version $$version"; \
	git push "$(GIT_REMOTE)" HEAD --follow-tags; \
	echo "Pushed tag v$$version"
