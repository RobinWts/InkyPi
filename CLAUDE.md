# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this is

This is a **fork of [InkyPi](https://github.com/fatihak/InkyPi)** used to **develop and maintain
InkyPi plugins**. The upstream app is the harness we run plugins against; the actual deliverables are
the plugins, each of which has its **own standalone Git repo**.

## ⚠️ Never commit plugins from this fork

Plugin repos get **flattened** into `src/plugins/<id>/` on install (their nested `.git` is lost).
Committing plugin changes from here does **not** reach the plugin's real repo and can break the layout.

→ Develop & test plugins here, then **copy the changed files into the plugin's standalone repo and
commit from there.** Details and per-plugin repo paths: see
[notes/plugin-development.md](notes/plugin-development.md) and the per-plugin notes.

## Context lives in `notes/`

`CLAUDE.md` stays short on purpose. Start from the index and follow the links:

→ **[notes/context-index.md](notes/context-index.md)** — architecture, development/run guide, plugin
development rules, per-plugin context, and the work-log.

## Work log

[notes/history.md](notes/history.md) is a reverse-chronological log of notable work and decisions.
**Read it at the start of a session**, and **append an entry** when you finish notable work or make a
decision/direction change (newest first, daily `## YYYY-MM-DD` tags). The file's header restates the
convention.

## Quick start

```bash
conda activate inkypi          # this workspace uses conda; the inkypi env has the deps installed
python src/inkypi.py --dev     # dev server, no hardware, web UI at http://localhost:8080
pytest tests/                  # tests
```
Full setup, commands, and the headless-Chrome rendering requirement: [notes/development.md](notes/development.md).
