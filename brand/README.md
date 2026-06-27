# Brand assets

Source vectors for the integration's brand images:

- `icon.svg` — square app icon.
- `logo.svg` — landscape logo (icon + wordmark).

Since Home Assistant 2026.3, custom integrations ship brand images locally from a
`brand/` folder **inside the integration**. The rendered PNGs therefore live in
`custom_components/energy_dashboard_sensors/brand/`:

- `icon.png` (256×256), `icon@2x.png` (512×512)
- `logo.png`, `logo@2x.png`

Local brand images take priority over the brands CDN; no submission to the
home-assistant/brands repository is required. HA loads them at startup, so
restart Home Assistant after adding or changing them.

Re-render after editing the SVGs:

```bash
python3 - <<'PY'
import cairosvg
T = "../custom_components/energy_dashboard_sensors/brand/"
cairosvg.svg2png(url="icon.svg", write_to=T+"icon.png", output_width=256, output_height=256)
cairosvg.svg2png(url="icon.svg", write_to=T+"icon@2x.png", output_width=512, output_height=512)
cairosvg.svg2png(url="logo.svg", write_to=T+"logo.png", output_width=450, output_height=140)
cairosvg.svg2png(url="logo.svg", write_to=T+"logo@2x.png", output_width=900, output_height=280)
PY
```
