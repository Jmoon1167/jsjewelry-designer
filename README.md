# JS Jewelry Ring Designer

Live at **https://design.jsjewelry.online** — customers build an engagement ring
(setting, center cut, carat, metal, stones), see it in real-time 3D, try it on
with their camera, and request it from JS Jewelry.

- Prices customers see: edit `src/jsj-pricing.js`, push to `main`.
- Metals and gemstones offered: `public/assets/library.json`.
- Build: `npm ci && npm run build` (Node 22). Output is a static site in `dist/`,
  served by the Cloudflare Worker in `worker.js` / `wrangler.jsonc`.

Based on the open-source viewer by shaarmander
(https://github.com/shaarmander/mobicats-jewels), MIT license — see `LICENSE`.
