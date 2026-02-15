#!/usr/bin/env bash
# PiSugar Button → InkyPi refresh script
# Call this script from the PiSugar Power Manager when the button is pressed
# to refresh and redisplay the current playlist item on the InkyPi display.

# InkyPi base URL (default: local InkyPi on port 80; use port 8080 for dev mode)
: "${INKYPI_URL:=http://127.0.0.1}"
endpoint="${INKYPI_URL}/pisugarbutton-api/refresh-current"

curl -s -X POST "$endpoint" -H "Content-Type: application/json" >/dev/null 2>&1
