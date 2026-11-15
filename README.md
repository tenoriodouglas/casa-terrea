# casa-terrea

Preliminary design of a single-story house on a 12 × 41 m lot, viewable in any browser (desktop and mobile).

**Live site:** https://tenoriodouglas.github.io/casa-terrea/

## Site
- **Planta**: dimensioned 2D floor plan (drawn as seen from the street), area table, green-area and accessibility notes.
- **Maquete 3D**: orbit model with preset views and image capture.
- **Passeio 3D**: real-time first-person walkthrough (WASD + mouse on desktop, joystick + drag on mobile).
- **Tour 360°**: ray-traced equirectangular panoramas with hotspots between rooms.
- **Renders**: ray-traced still images.
- **[Passeio realista](passeio-realista.html)**: Gaussian-splat walkthrough rendered with [Spark](https://sparkjs.dev); loads `splats/<room>.spz` when present.

Deep links: `#planta`, `#maquete`, `#passeio`, `#tour360`, `#renders`.

## Program
- Living/dining, kitchen with island, entrance hall.
- Powder room and winter garden between the living area and the bedroom wing.
- 3 bedrooms (1 master suite) + home office. Bedroom corridor (1.30 m) gives access to the laundry (side door to the clothesline), shared bathroom, bedrooms 2 and 3, master suite and office.
- Master suite with walk-in closet and accessible bathroom.
- Compact covered grill: sink, wood-fired grill and pizza oven sharing the same chimney (no dining area), herb planter beside it.
- Lawn, fruit trees, compost bin and 5 raised vegetable beds (45 m²).
- Accessibility (NBR 9050 basis): 0.90 m doors, 1.50 m turning circles in bathrooms, curbless showers.
- Wood floors throughout (wood-look porcelain in wet areas); lawn outside, including a grass driveway. Ceiling height 3.00 m, built area ≈ 196 m².

## Realistic walkthrough workflow
1. **World Labs Marble** (generative 3D worlds): upload a panorama from `renders/pano/` as a *Panorama* input, export the world as `.spz` and commit it to `splats/<room>.spz` (e.g. `splats/sala.spz`). `passeio-realista.html` picks it up automatically.
2. **Twinmotion** (free for individuals and companies under US$ 1M revenue): import `model/casa.glb`, apply realistic materials and animated vegetation, and export path-traced images, 360° panoramas or walkthrough videos.

## Files
- `index.html`: the whole site (Three.js r128).
- `passeio-realista.html`: splat viewer (vendored Three.js 0.180 + Spark 2.4 in `vendor/`).
- `model/casa.glb`: 3D model export for external renderers.
- `renders/`: ray-traced stills; `renders/pano/`: 360° panoramas.
