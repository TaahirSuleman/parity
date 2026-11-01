PY := .venv/bin/python
PORT ?= 8080

.PHONY: setup venv web vendor-axe test test-web demo dev serve clean

setup: venv web vendor-axe build-web ## Install everything (brew toolchain, venv, Chromium, web deps) and build the SPA
	@echo "setup complete"

venv:
	@command -v uv >/dev/null || brew install uv
	@command -v python3.12 >/dev/null || brew install python@3.12
	@test -d .venv || uv venv --python 3.12 .venv
	uv pip install --python $(PY) -e ".[dev]" --config-settings editable_mode=compat
	$(PY) -m playwright install chromium
	@chflags nohidden .venv/lib/python*/site-packages/*.pth 2>/dev/null || true  # macOS may flag the editable .pth hidden; CPython 3.12.16 then skips it

web:
	@command -v npm >/dev/null || brew install node
	@test -f web/package.json && (cd web && npm ci) || echo "web/ not created yet"

vendor-axe:
	@mkdir -p parity/vendor
	@test -f web/node_modules/axe-core/axe.min.js || (cd web && npm i --no-save axe-core@4.14.0)
	cp web/node_modules/axe-core/axe.min.js parity/vendor/axe.min.js

test:
	$(PY) -m pytest

test-web:
	cd web && npm test

build-web:
	cd web && npm run build

demo: build-web ## One-command local run: build the SPA, serve on :$(PORT), open the workbench
	( sleep 2 && open http://127.0.0.1:$(PORT)/ ) &
	$(PY) -m uvicorn parity.app:create_app --factory --port $(PORT)

serve:
	$(PY) -m uvicorn parity.app:create_app --factory --port $(PORT) --reload

clean:
	rm -rf .pytest_cache parity/static web/dist
