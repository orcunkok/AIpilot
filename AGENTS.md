# Building this repo

YAGNI. Build the asked slice. Do not add tools, skills, frameworks, config, or abstractions “for later.”

- **Start small.** A handful of meta-tools and one or two skills. Not tens, not hundreds.
- **Do not go beyond.** If the task is a doc, write the doc. If the task is one tool, do not invent a registry framework.
- **Simple is the goal.** Overengineering is a failure. Prefer one module over a package tree until a second caller exists.
- **No heavy agent frameworks** (LangGraph, CrewAI, robotics middleware). Thin loop + OpenAI adapter.
- **Do not expand scope while here.** No extra README, extra markdown, or curses-mock refactors unless asked.
- **Match what exists.** Python, stdlib first. The terminal UI stays a viewer until a loop is worth showing.
- **When in doubt, ask or stop.** Do not fill gaps with speculative architecture.
- **Update `HARNESS_DESIGN.md` when harness behavior actually changes** — not on every thought.

No `.cursor/rules` unless asked. This file is enough.
