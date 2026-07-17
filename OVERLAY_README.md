# Overlay v4

Changes:
- Fixed host-page backgrounds so the overlay background transparency slider reveals windows/gameplay behind it.
- Drag the overlay from any empty area while Edit Mode is enabled.
- Resize from all four edges and all four corners.
- Added Midnight, Crimson, Emerald, Solar, and Frost themes.
- Added a custom accent color picker and font selector.
- Existing aura rarity, biome, local day/night, session time, corner snapping, and click-through behavior are preserved.

Run:
1. `py -3.12 -m pip install -r requirements.txt`
2. `py -3.12 main.py`
3. Open Other Features > In-Game Status Overlay.

## v5 transparency and rounded-window fix

- Transparency is now applied to the native Windows overlay through `WS_EX_LAYERED` / `LWA_ALPHA`, so Roblox and other windows are genuinely visible behind it.
- The native overlay window is clipped with a Win32 rounded region, removing the square outer corners.
- The rounded region is recalculated while resizing from any edge or corner.
- Because the native window is faded, text fades together with the panel. This is required for reliable real transparency with the embedded WebView2 window.

## Detector integration

The overlay does not run duplicate detection. It reads the same tracker state used by the existing tabs:

- **Biome**: `current_biome`, updated by the Biome detector.
- **Last Aura / Aura Rarity**: updated only when the Aura detector accepts a roll, while honoring the overlay minimum-rarity setting.
- **Last Merchant**: updated when either Merchant chat OCR or the Merchant interaction/name OCR accepts Mari, Jester, or Rin.

This keeps the overlay synchronized with the macro's existing Biomes, Auras, and Merchant systems.
