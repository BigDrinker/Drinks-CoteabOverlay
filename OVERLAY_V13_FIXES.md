# Overlay v13 fixes

- Preserves WebView2's layered window style so background-only CSS transparency no longer turns white.
- Uses the native Windows move/resize loop directly for reliable resizing from every edge and corner.
- Saves the exact native overlay bounds immediately after moving/resizing and before Edit Mode is disabled.
- Prevents the settings UI from overwriting the newly saved custom position with stale config data.
- Enlarges invisible edge/corner resize targets.

Close all older macro/overlay processes before starting this version.
