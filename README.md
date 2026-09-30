# Mali Ya Rona AI — Monitor Backend

Every time the dashboard asks for data, it reloads the external seed data.
This means if another system changes the external dataset, the monitor
can rescan it on the next request — important for how this backend's
architecture works.

## Running with the AI provider (Gemini)

This backend can use Google's Gemini API. To run it:

1. Get your own Gemini API key from https://aistudio.google.com
2. Set it as an environment variable (never commit a real key to this file):
3. Run: