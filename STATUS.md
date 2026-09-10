# Status we feed the AI — proposal

Not implemented yet. Send a compact current snapshot with each meaningful event.
Do not resend the entire flight history or ask the AI to fetch status it already has.
Unknown values stay unknown.

## Mission

- Objective, departure, and intended destination.
- Current phase: parked, taxi, takeoff, flight, hold, approach, landing, or shutdown.
- Current plan and next intended action, kept separate from confirmed facts.

## Aircraft — actual observations

- Current airport/fix or position.
- On ground or airborne.
- Actual altitude, speed, and heading.
- Engine status, flaps, gear, and parking brake.
- Active faults or warnings.

## Selected settings

- Target altitude, speed, and heading.
- Altimeter setting, radio frequency, and transponder code.
- Requested configuration preset.

A selected altitude of 5,000 feet does not mean we have reached 5,000 feet.
Requested gear down does not mean gear down is confirmed.

## ATC

- Latest received transcript and current controller.
- Current clearances and restrictions, linked to their source message.
- Whether a readback was sent.
- Requests still awaiting a reply.
- Unclear or conflicting instructions that need clarification.

## Progress and problems

- Pending actions: ID, requested action, and execution status.
- Latest completed or failed action and its observed result.
- Required ground services and their status.
- Active checklist/procedure and outstanding items.
- Unresolved faults and readiness for the next mission.

## Relevant surroundings

- Current airport/runway availability, weather, and taxi-route restrictions.
- Selected route and its supplied estimates.
- Relevant aircraft limits or procedure information when needed.

Keep the full reference data in files. Supply only the parts relevant to the
current decision; the AI can request more. No fuel calculation is needed.

## When to call the AI

A new mission, ATC message, meaningful action result, or unexpected event.
Send the current snapshot plus what just changed. The program updates confirmed
state from observations/results. The AI chooses actions; it does not edit facts.
