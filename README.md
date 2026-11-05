# skills

Agent skills for Claude Code and other agents that read `SKILL.md`.

## Install

```sh
npx skills add hfrpotgieter/skills
```

`grill-review` needs the `grilling` skill (and `grill-me`, its slash command) from [mattpocock/skills](https://github.com/mattpocock/skills):

```sh
npx skills add mattpocock/skills   # pick grilling and grill-me
```

## Skills

- **grill-review**: after a grilling session, drafts the agreed change in a scratch checkout and writes an HTML review: the decisions, before/after Mermaid diagrams, and the real diff, for you to sense-check before anything touches your working tree. Run it with `/grill-review`.
