import { estimate } from "./prices.js";
import { PRICING, priceRange, onSpecial } from "./jsj-pricing.js";
import { designLink } from "./share.js";

const el = (id) => document.getElementById(id);
const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
let lastLabel,
  timer,
  loading = false;
function reels(label) {
  const host = el("estimate-reels");
  const parts = Array.from(label, (c, place) => {
    if (!/\d/.test(c)) return document.createTextNode(c);
    const slot = document.createElement("span"),
      strip = document.createElement("span");
    slot.className = "digit-slot";
    strip.className = "digit-strip";
    strip.style.animationDelay = place * 12 + "ms";
    for (let i = 0; i < 5; i++) {
      const digit = document.createElement("i");
      digit.textContent = String((Number(c) + i * 3) % 10);
      strip.append(digit);
    }
    slot.append(strip);
    return slot;
  });
  host.replaceChildren(...parts);
}
export function loadingEstimate() {
  clearTimeout(timer);
  loading = true;
  lastLabel = undefined;
  el("estimate").setAttribute("aria-busy", "true");
  el("estimate-live").textContent = "Calculating price estimate";
  for (const id of ["price-range", "price-metal", "price-center", "price-accents"])
    el(id).textContent = "";
  el("price-accents-label").hidden = el("price-accents").hidden = true;
  reels(matchMedia("(prefers-reduced-motion:reduce)").matches ? "…" : "$0,000");
}
function summary(studio) {
  const s = studio.state,
    lib = studio.lib;
  const name = (list, id) => list.find((x) => x.id === id)?.name ?? id;
  return [
    name(lib.gems, s.center) + " " + name(lib.settings, s.setting).toLowerCase(),
    name(lib.cuts, s.cut).toLowerCase() + " cut",
    s.carats.toFixed(2) + " ct center",
    name(lib.metals, s.metal),
  ].join(", ");
}
export function quoteLink(studio, range, special) {
  const url = new URL(PRICING.quoteUrl);
  url.searchParams.set("interest", "engagement");
  let piece = summary(studio);
  if (special) piece += " (special " + money.format(PRICING.special.price) + ")";
  else if (range)
    piece +=
      " (designer estimate " +
      money.format(range[0]) +
      "–" +
      money.format(range[1]) +
      ")";
  url.searchParams.set("piece", piece);
  url.searchParams.set("design", designLink(studio));
  url.hash = "consult";
  return url.href;
}
export function updateEstimate(studio) {
  if (!studio) {
    el("estimate").setAttribute("aria-busy", "false");
    el("estimate").hidden = true;
    return;
  }
  const e = estimate(studio),
    special = onSpecial(studio),
    range = special ? [PRICING.special.price, PRICING.special.price] : priceRange(e),
    lib = studio.lib,
    s = studio.state;
  const sp = PRICING.special;
  el("estimate").classList.toggle("on-special", special);
  el("estimate-label").textContent = special ? sp.label : "Starting at";
  el("estimate").setAttribute("aria-busy", "false");
  el("price-range").textContent = special
    ? money.format(sp.price)
    : range
      ? money.format(range[0]) + " – " + money.format(range[1])
      : "Quote on request";
  if (e) {
    el("price-metal").textContent =
      lib.metals.find((m) => m.id === s.metal).name +
      " · ~" +
      e.grams.toFixed(1) +
      " g";
    el("price-center").textContent =
      s.carats.toFixed(2) +
      " ct " +
      lib.gems.find((g) => g.id === s.center).name.toLowerCase();
    el("price-accents-label").hidden = el("price-accents").hidden = !e.count;
    el("price-accents").textContent =
      e.count + " stones · " + e.accentCarats.toFixed(2) + " ctw";
  }
  el("price-note").textContent = special
    ? sp.note
    : sp && s.center === sp.stone
      ? "Tip: " + sp.note.replace(/^Special: /, "")
      : range
        ? ""
        : "We price " +
      (e?.missing.join(", ") || "this design") +
      " by hand. Request this ring for a quote.";
  el("quote-link").href = quoteLink(studio, range, special);
  const label = range ? money.format(range[0]) : "Quote";
  if (label === lastLabel && !loading) return;
  lastLabel = label;
  loading = false;
  clearTimeout(timer);
  reels(label);
  timer = setTimeout(() => {
    el("estimate-live").textContent = special
      ? "Special price " + label
      : range
        ? "Starting at " + label
      : "Price on request";
  }, 380);
}
