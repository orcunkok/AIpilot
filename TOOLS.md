# Tools the AI can use — proposal

These are planned tools, not implemented yet. Each asks the mock aircraft to do
something and returns a result. No physics or direct actuator control.

## Read information

- `get_status()` — request fresh aircraft status when needed. Normally status is already included with an event.
- `get_airport(airport)` — runways, weather, taxi routes, and available services.
- `get_routes(origin, destination)` — supplied route options and precomputed estimates.
- `get_procedure(name)` — supplied normal or emergency procedure.

## Communicate

- `send_atc(message)` — send a plain-text request, readback, or report.
- `request_assistance(reason)` — ask for help.

Incoming ATC is plain text from the terminal or, later, speech-to-text.
Sending a request does not grant clearance.

## Set the aircraft

- `set_altitude(feet)` — select target altitude.
- `set_speed(knots)` — select target speed.
- `set_heading(degrees)` — select target heading.
- `set_altimeter(pressure_hpa)` — set the altimeter.
- `set_radio(frequency)` — select radio frequency.
- `set_transponder(code)` — select squawk code.
- `set_configuration(preset)` — takeoff, cruise, approach, or landing settings.
- `set_flaps(position)` — request a flap setting.
- `set_gear(position)` — request gear up or down.
- `set_parking_brake(enabled)` — set or release the brake.

## Operate

- `request_ground_service(service)` — request a supplied service.
- `run_checklist(name)` — check observed settings against a supplied checklist.
- `start_aircraft()` — start the aircraft.
- `taxi(route, destination)` — taxi to a runway holding point or stand.
- `takeoff(runway)` — execute the supplied takeoff capability.
- `fly_to(destination)` — follow a supplied route to an airport or fix.
- `hold(fix)` — hold at a supplied location.
- `approach(airport, runway)` — begin the approach.
- `go_around()` — discontinue landing using the supplied capability.
- `land(airport, runway)` — land.
- `park(stand)` — park at the stand.
- `shutdown_aircraft()` — shut down.
- `execute_procedure(name)` — execute a supplied emergency capability.

## Keep the interface small

This is the full proposed list, not a requirement to send every tool on every AI
request. Supply tools relevant to the current situation, including information,
communication, and applicable emergency tools. Independent settings can be requested
together; dependent actions wait for results.

An action returns an ID and a status: accepted, rejected, in progress, completed,
or failed. Accepted does not mean completed. The program handles waiting and
reports the result; an extra AI call is not needed just to wait.
