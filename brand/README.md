# Brand assets

- `icon.svg` — source vector icon.
- `icon.png` — 256×256 (Home Assistant brands requirement).
- `icon@2x.png` — 512×512.

Home Assistant only shows the logo on the integrations page once the assets are
merged into the [home-assistant/brands](https://github.com/home-assistant/brands)
repository. To submit, add these files under
`custom_integrations/energy_dashboard_sensors/` in that repo (the folder name
must match the integration `domain`). The same `icon.png` can be reused as
`logo.png` if no separate wordmark is provided.

Re-render the PNGs after editing the SVG:

```bash
python3 -c "import cairosvg; \
  cairosvg.svg2png(url='icon.svg', write_to='icon.png', output_width=256, output_height=256); \
  cairosvg.svg2png(url='icon.svg', write_to='icon@2x.png', output_width=512, output_height=512)"
```
