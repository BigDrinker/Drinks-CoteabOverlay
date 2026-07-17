Coteab Native Overlay - Step 4

This build connects the proven native overlay to the macro's real:
- RUNNING / STOPPED detection state
- Session timer

Run:
  py -3.12 -m pip install -r requirements.txt
  py -3.12 main.py

Then enable the overlay from the macro's Overlay settings.

Controls inside the overlay:
- Drag the header to move
- Drag any edge/corner to resize
- Mouse wheel or +/- changes background-only transparency
- Esc closes only the overlay test window

This is intentionally Step 4 only. Biome, aura, merchant, themes, and layout controls will be connected after this status/session integration is confirmed stable.
