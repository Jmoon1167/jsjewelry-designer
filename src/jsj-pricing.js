/* JS Jewelry customer price estimate.
   Edit these numbers to change what customers see. Push to GitHub and the
   live designer updates on its own.

   Range = metal x metalMarkup + stones x stoneMarkup + labor (+ per side stone)
   Stone prices come from public retail indices (see prices.js), so their
   markup stays close to 1. Metal comes from the live gold/platinum spot price. */
export const PRICING = {
  metalMarkup: [1.6, 2.0], // casting loss, alloy, finishing
  stoneMarkup: [1.0, 1.2],
  labor: [350, 550], // CAD, casting, setting, polish
  perAccentStone: [6, 10], // setting each side / pave stone
  minimum: 600,
  roundTo: 50,
  quoteUrl: "https://jsjewelry.online/about/",
};

export function priceRange(e) {
  if (!e || e.total == null) return null;
  const p = PRICING;
  const at = (i) =>
    e.metalCost * p.metalMarkup[i] +
    (e.center + e.accents) * p.stoneMarkup[i] +
    p.labor[i] +
    e.count * p.perAccentStone[i];
  const low = Math.max(p.minimum, Math.floor(at(0) / p.roundTo) * p.roundTo);
  const high = Math.max(low, Math.ceil(at(1) / p.roundTo) * p.roundTo);
  return [low, high];
}
