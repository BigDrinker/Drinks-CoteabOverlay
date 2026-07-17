# Native Overlay Step 5

This build adds the live **Biome** row to the proven native overlay.

The overlay reads the same `current_biome` value used by the macro's existing biome detector. It does not perform separate OCR or duplicate detection.

## Test

1. Start the macro and enable the overlay.
2. Confirm Macro Status and Session still update.
3. Let the normal biome detector identify a biome.
4. Confirm the overlay updates to the same biome shown by the macro.
5. Confirm moving, resizing, transparency, and saved bounds still work.
