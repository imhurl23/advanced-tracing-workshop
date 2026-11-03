# =============================================================================
# advanced-tracing-workshop — operator entry points
#
# Prereqs (install from WELCOME.md before running any target): uv, bt.
# Auth/config: fill .env (Braintrust API key + your project), then load it into your
# shell: set -a; source .env; set +a  (see docs/PARTICIPANT.md step 2).
# See SEEDING_MILESTONES.md for the full build plan.
# =============================================================================

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# ANSI helpers
BOLD := \033[1m
DIM  := \033[2m
OK   := \033[32m
WARN := \033[33m
ERR  := \033[31m
END  := \033[0m

# Every target that talks to Braintrust needs a project. It comes from .env, loaded
# into the shell (docs/PARTICIPANT.md step 2), which both bt and the Python code read.
PROJECT_GUARD = @test -n "$${BRAINTRUST_DEFAULT_PROJECT:-}" || { printf "$(ERR)BRAINTRUST_DEFAULT_PROJECT is not set.$(END) Fill it in .env, then run: set -a; source .env; set +a\n"; exit 1; }

# Full-seed size (override: `make seed COUNT=200`).
COUNT ?= 500

# Guard for targets whose script isn't written yet — points at the milestone.
define require_script
@test -f $(1) || { printf "$(WARN)$(1) not built yet — see SEEDING_MILESTONES.md $(2).$(END)\n"; exit 2; }
endef

# -----------------------------------------------------------------------------
.PHONY: help
help:
	@echo ""
	@printf "$(BOLD)advanced-tracing-workshop$(END) — make targets\n"
	@echo ""
	@printf "$(BOLD)Hero$(END)\n"
	@echo "  make prepare       ONE-SHOT: create project → Topics + Patterns → smoke seed → full seed (prepare a project)"
	@echo ""
	@printf "$(BOLD)Setup$(END)\n"
	@echo "  make setup         uv sync + create .env (checks uv/bt are installed)"
	@echo "  make agent         run the agent's Streamlit app (live demo — PARTICIPANT step 3)"
	@echo ""
	@printf "$(BOLD)Provision (pre-work)$(END)\n"
	@echo "  make project       create the project if it doesn't exist"
	@echo "  make patterns      enable the Patterns automation on your project (daily 9am PT)"
	@echo "  make seed-smoke    enable Topics + Patterns (upstream) + seed 10 traces, then verify"
	@echo "  make seed          seed COUNT traces (default 500; runs seed-smoke first)"
	@echo "  make top-up        seed COUNT more traces only (keeps Patterns active before the workshop)"
	@echo "  make provision     alias for seed-smoke — the topics + patterns + smoke verify gate"
	@echo "  make topics        enable Topics on your project (clustering; not the key finding)"
	@echo "  make copy-dataset DATASET=<name>   copy a super-stonks dataset to all other org projects"
	@echo ""
	@printf "$(BOLD)Workshop (your own project)$(END)\n"
	@echo "  make curate-dataset  turn a super-stonks Pattern's evidence into a dataset in your project"
	@echo "  make push-scorer     push the tool-success scorer (code scorer)"
	@echo "  make automations     score every tool span online with it (via API)"
	@echo "  (experiments run via: bt eval src/super_stonks/evals/qa_eval.py)"
	@echo ""

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
.PHONY: setup
setup:
	@command -v uv >/dev/null 2>&1 || { echo "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	@command -v bt >/dev/null 2>&1 || { echo "bt not found. Install: curl -fsSL https://bt.dev/cli/install.sh | bash"; exit 1; }
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env. Fill in BRAINTRUST_API_KEY and BRAINTRUST_DEFAULT_PROJECT."; else echo ".env already exists; keeping your values. Check the defaults in docs/PARTICIPANT.md step 2."; fi
	uv sync
	@echo "Setup complete. Fill .env, then run: set -a; source .env; set +a"

# -----------------------------------------------------------------------------
# Live demo
# -----------------------------------------------------------------------------
.PHONY: agent
agent:
	uv run streamlit run src/super_stonks/app.py

# -----------------------------------------------------------------------------
# Provision
# -----------------------------------------------------------------------------
# Create the project if it doesn't exist yet (first step of the seed chain).
.PHONY: project
project:
	$(PROJECT_GUARD)
	@if bt projects list --json | grep -q "\"name\":\"$$BRAINTRUST_DEFAULT_PROJECT\""; then \
		printf "$(DIM)Project $$BRAINTRUST_DEFAULT_PROJECT already exists.$(END)\n"; \
	else \
		bt projects create "$$BRAINTRUST_DEFAULT_PROJECT" && printf "$(OK)Created project $$BRAINTRUST_DEFAULT_PROJECT.$(END)\n"; \
	fi

.PHONY: patterns
patterns: project
	$(PROJECT_GUARD)
	uv run python -m super_stonks.provision.patterns

# Topics still runs during seeding for clustering; Patterns carries the key finding.
.PHONY: topics
topics: project
	$(PROJECT_GUARD)
	@printf "$(DIM)Enabling Topics on $$BRAINTRUST_DEFAULT_PROJECT …$(END)\n"
	-bt topics config enable --name "Workshop Topics" --topic-window 1d --generation-cadence 1h --no-input

# Topics + Patterns are upstream of any seeding, so seed-smoke depends on both; the full
# seed depends on seed-smoke. `make seed` therefore does: project → topics + patterns →
# 10 smoke → COUNT.
# Each run draws a fresh random mix of questions (pass SEED=N to reproduce one).
SEED_ARGS = $(if $(SEED),--seed $(SEED),)

.PHONY: seed-smoke
seed-smoke: topics patterns
	$(PROJECT_GUARD)
	$(call require_script,src/super_stonks/seed/seed.py,M3)
	uv run python -m super_stonks.seed.seed --count 10 $(SEED_ARGS)
	@printf "$(OK)10 smoke traces sent.$(END) Verify: bt view logs --list-mode spans, then 'make seed'.\n"

.PHONY: seed
seed: seed-smoke
	$(PROJECT_GUARD)
	$(call require_script,src/super_stonks/seed/seed.py,M3)
	uv run python -m super_stonks.seed.seed --count $(COUNT) $(SEED_ARGS)

# Top-up = more traffic only (no Topics/Patterns/smoke step). Patterns needs matching traces in
# the last two weekdays to keep a pattern active, so run this shortly before the workshop.
.PHONY: top-up
top-up:
	$(PROJECT_GUARD)
	uv run python -m super_stonks.seed.seed --count $(COUNT) $(SEED_ARGS)

# Provision = the topics + patterns + smoke verify gate (alias for seed-smoke).
.PHONY: provision
provision: seed-smoke
	@printf "$(OK)Provisioned:$(END) Topics + Patterns enabled + 10 smoke traces. Verify the gate, then run 'make seed'.\n"

# Hero one-shot: prepare a project end to end. The dependency chain runs
# topics + patterns → seed-smoke (10) → seed (COUNT); this target just adds the headline.
# Prereqs: `make setup` + `.env` sourced (PARTICIPANT step 2) (API key + project) first.
.PHONY: prepare
prepare: seed
	@printf "$(OK)✔ Project prepared$(END) on $$BRAINTRUST_DEFAULT_PROJECT: Topics + Patterns enabled, smoke + full traces seeded (share-class tickers planted).\n"

# Copy a dataset from the primary project (super-stonks) to every other org project.
# bt enumerates projects (API-key auth); the SDK copies the rows.
.PHONY: copy-dataset
copy-dataset:
	@test -n "$(DATASET)" || { printf "$(ERR)Usage: make copy-dataset DATASET=<name>$(END)\n"; exit 1; }
	uv run python -m super_stonks.provision.copy_dataset "$(DATASET)"

# -----------------------------------------------------------------------------
# Online scoring
# -----------------------------------------------------------------------------
# Push the tool-success scorer (a Python code scorer). Runs from src/ so the bundled
# module path is `super_stonks.evals.push_assets`; --runner points bt at the venv python.
.PHONY: push-scorer
push-scorer:
	$(PROJECT_GUARD)
	cd src && bt functions push --file super_stonks/evals/push_assets.py \
		--language python --runner "$(CURDIR)/.venv/bin/python" \
		--if-exists replace -p "$$BRAINTRUST_DEFAULT_PROJECT" --yes

.PHONY: curate-dataset
curate-dataset:
	$(PROJECT_GUARD)
	uv run python -m super_stonks.provision.curate_dataset

.PHONY: automations
automations:
	$(PROJECT_GUARD)
	uv run python -m super_stonks.provision.configure
