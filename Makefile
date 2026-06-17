# Aegoria — top-level developer Makefile.
#
# The default app runs as a LEAN docker compose stack (console + api). Heavy
# data infra lives behind the compose `scaleout` profile and is opt-in.
#
# Run targets from the REPO ROOT. The Dockerfiles use the repo root as their
# build context (set `context: ..` in compose) so the images can see engine/,
# control-plane/, sdk/, domain-packs/ and apps/console/.

COMPOSE        ?= docker compose
COMPOSE_FILE   ?= deploy/docker-compose.yml
COMPOSE_CMD    := $(COMPOSE) -f $(COMPOSE_FILE)

PY             ?= engine/.venv/bin/python

.DEFAULT_GOAL := help

.PHONY: help up down logs demo api-dev console-dev scaleout

help: ## Show this help.
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Build + start the lean stack (console:3000, api:8000).
	$(COMPOSE_CMD) up --build

down: ## Stop and remove the stack.
	$(COMPOSE_CMD) down

logs: ## Follow logs from the running stack.
	$(COMPOSE_CMD) logs -f

scaleout: ## Start the opt-in scale-out mesh (minio, iceberg, spark, trino, redpanda, dagster).
	$(COMPOSE_CMD) --profile scaleout up --build

demo: ## Run the engine end-to-end locally (bootstrap, doctor, catalog) via the venv.
	$(PY) -m aegoria_core.cli version
	$(PY) -m aegoria_core.cli doctor
	$(PY) -m aegoria_core.cli packs
	$(PY) -m aegoria_core.cli catalog

api-dev: ## Run the control-plane API locally with reload (no Docker).
	$(PY) -m uvicorn control_plane.app:app --host 0.0.0.0 --port 8000 --reload

console-dev: ## Run the console dev server locally (no Docker).
	pnpm --filter @aegoria/console dev
