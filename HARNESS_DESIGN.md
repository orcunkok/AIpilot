# Harness design

PIC supervisor harness. The LLM is the pilot. Automation owns continuous control. The harness decides when the model runs and what tiny world it sees. This is not a joystick, not a flight demo, not a 1 Hz telemetry prompt.

If nothing needs a pilot, zero tokens.

```
world/automation
  → event (operator, ATC in, intent done/fail, phase change)
    → assemble context
      → model
        → local tools (args only, no chat history)
          → mutate world or load skill
            → compact this wake
              → wait
```

## When the model wakes

Wake on: operator message, inbound ATC, intent completed / failed / blocked, phase change.

Do not wake on airspeed or other ticks. Snapshot is fresh *when* you wake; you do not stream it.

Inbound ATC is an event, not something the model polls. Outbound radio is `xmit(text)`.

Later, not v0: fault/emergency wakes, watchdog/timer wakes.

## Three stores

Do not confuse them.

1. **UI transcript** — what a human sees (`Session.messages`, fed from `harness.transcript`). Not what the model gets.
2. **Model context** — rebuilt every wake. Not a growing chat log.
3. **Run log** — full JSONL under `runs/<id>.jsonl` for replay and tests.

Tools never receive chat history. They are local Python functions. They read/write the world and return a short result. The model sees that result as a tool message *in this wake only*.

## What is sent every wake

Stable prefix:

- **Kernel** — you are PIC; aviate > navigate > communicate; never invent a clearance; read back before acting; do not poll.
- **Skill catalog** — name + one-line when-to-use. One flat list.
- **Bound tools (v0)** — `load_skill`, `xmit`, `set_intent`.

Replaced every wake (not appended):

- **Working snapshot** — phase, position, engine, active clearances, pending ATC, active intent, loaded skills, mission. Overwrite the previous snapshot block.

Small durable block (updated in place for the run):

- Mission, structured clearance log, constraints.

Compacted prior wakes (not the raw chat):

- Trigger, intents, outcomes, ATC that mattered.
- Last N ATC transmissions kept verbatim (readback needs exact words). Older radio becomes one line.
- Drop raw status dumps and long skill/reference text from older wakes; keep the conclusion.

This wake only (standard tool loop):

```
[event as user message]
→ model may call tools
→ append assistant tool_calls + tool results to THIS wake
→ call model again
→ repeat until text or a terminal action
```

Across wakes: do not resend previous tool JSON. Inside a wake: do send this wake’s tool I/O. After the wake ends, write a TurnRecord and drop the raw dump from the next prefix.

## What is not sent

- Raw telemetry stream
- Previous wakes’ tool JSON
- Unloaded skill bodies
- Full aviation manuals
- The UI transcript

## What persists

| Thing | Lifetime |
| --- | --- |
| `runs/<id>.jsonl` | Disk, whole run |
| Durable memory (mission, clearances, constraints) | Memory + run log, one run |
| Working snapshot | Current only; replaced each wake |
| Model context | Rebuilt each wake |
| UI transcript | Session display only |
| Loaded skill body | Until the run ends or it is replaced by another load |

A **run** is one flight/scenario: fresh kernel and catalog, empty compact history, world reset. A **wake** is one event-triggered model session, possibly many tool round-trips. Do not carry clearances across runs.

Wake kill switches (already named in `.env.example`): `FLIGHTOPS_MAX_CALLS`, `FLIGHTOPS_TIMEOUT`.

## Skills vs tools vs intents

- **Skill** — a procedure pack (`skills/<name>/SKILL.md`). Catalog stub always visible; body loaded with `load_skill`. One disclosure level; no nested skill trees.
- **Tool** — a local function. v0 binds three. Loading a skill does not dump extra schemas.
- **Intent** — high-level work for automation (`set_intent(taxi, …)`), not twenty micro-calls. Automation (even a mock) runs and emits done / fail / blocked.

## Compaction rubric

After each wake, persist a TurnRecord: id, event, snapshot digest, loaded skills, intents, tool outcomes, atc in/out.

Rebuild next context from TurnRecords:

- Keep: active clearances, unread / un-readback ATC, mission, loaded skill names
- Summarize: completed taxi segments, old radio
- Drop: raw status JSON, long reference pages

v0 does not auto-summarize to a token budget. If the compact prefix gets large, fix the assembler; do not add a summarizer until asked.

## v0 inventory

Code: [`harness.py`](harness.py) (world, snapshot, memory, assemble, tools, wake, JSONL) and [`adapter.py`](adapter.py) (OpenAI + scripted test double).

Skills: [`skills/taxi`](skills/taxi/SKILL.md), [`skills/atc-phraseology`](skills/atc-phraseology/SKILL.md). Tools: `load_skill`, `xmit`, `set_intent`.

UI: [`terminal_ui.py`](terminal_ui.py) `Session` is the submit path for curses and the plain terminal. Conversation pane is `harness.transcript` (plus a SYSTEM banner). Sidebar is the current snapshot. `/atc TEXT` is inbound radio and the clearance string (substring match). `/demo` injects the canned taxi ATC line. `/clear` clears the display list only.

Tests: [`tests/test_harness.py`](tests/test_harness.py) and [`tests/test_session.py`](tests/test_session.py) (no model). [`tests/test_live_wake.py`](tests/test_live_wake.py) skips without `OPENAI_API_KEY`.

Later, not now: `search_skills`, `search_tools`, `get_detail`, `note`, `cancel_intent`, phase affordances, watchdog, token-budget summarizer, extra skills.

## Debug checklist

- Model “forgot” a clearance → check durable memory and last-N ATC, not the UI pane.
- Tokens exploded → snapshot was appended instead of replaced, or a skill body was left in the prefix after it should have been dropped, or old tool JSON was not compacted.
- Model never woke → event was not enqueued; telemetry ticks are not events.
- Tool “didn’t see context” → expected. Tools get args only.
- Readback wrong → last ATC in compact history must still be verbatim.
