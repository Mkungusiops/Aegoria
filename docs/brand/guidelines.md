# Aegoria — Brand Guide

The brand is the trust surface. Aegoria handles planetary, often sensitive data across every
market — the look and language must read as **trustworthy, precise, and alive**. This guide is
the single source of truth; the machine-readable tokens live in `brand/tokens.json` and the
marks in `brand/`.

---

## 1. Name & tagline

- **Name:** **Aegoria** — evokes *aegis* (a shield, protection) and a *territory* that spans
  domains. A platform that protects data and gives every market a home.
- **Tagline:** **"One planet. Every domain. Data you can trust."**
  - *One planet* — planet-scale, shared commons.
  - *Every domain* — market-agnostic; one core for all.
  - *Data you can trust* — quality, provenance, privacy, sovereignty by default.

Always write the name as **Aegoria** (title case). The wordmark renders it as `AEGORIA` in
tracked caps (see `brand/logo-wordmark.svg`); that is a *typographic* treatment of the logo,
not the way to write the name in prose.

---

## 2. Signature colour — **Auralis** `#16E0C4`

Auralis is Aegoria's **invented signature hue** — a living cyan-jade, "the colour of data
becoming knowledge."

> **Story.** Auralis is cool enough to read as *trustworthy and clinical*, alive enough to
> feel like *signal moving through a planetary nervous system*. It is the through-line of the
> brand: the moment raw data crosses into something you can rely on. (`brand/tokens.json` →
> `brand.signatureColour`.)

**Usage**
- The **primary brand accent**: the logo aperture, key actions, focus/active states, "live"
  indicators, and the auralis KPI tone.
- Pair with **Auralis Deep** `#0BA98F` for hover/pressed and depth, and **Auralis Glow**
  `rgba(22,224,196,0.16)` for ambient halos and the `shadow.glow`.
- The signature gradient (`gradient.auralis`): `linear-gradient(135deg, #16E0C4 0%, #21D6C9
  55%, #7B61FF 100%)` — Auralis flowing into Pulse. Reserve it for hero/logo moments.
- **Do not** flood large surfaces with solid Auralis; it is an *accent* against the dark
  Veil. Keep it for signal, not background.

---

## 3. Palette

Aegoria is a **dark-first** brand. The canvas is deep space (Veil); colour is signal.

### Foundation
| Token | Hex | Role |
|-------|-----|------|
| **Veil** | `#070A12` | Primary background — the deep canvas |
| Surface 1 | `#0B0F1A` | Raised surface |
| Surface 2 | `#121829` | Cards / panels |
| Surface 3 | `#1A2236` | Elevated / hover surfaces |
| Hairline | `#1E2740` | Borders, dividers, table rules |

### Signature
| Token | Hex | Role |
|-------|-----|------|
| **Auralis** | `#16E0C4` | Signature accent, primary actions, live |
| Auralis Deep | `#0BA98F` | Hover/pressed, depth |
| Auralis Glow | `rgba(22,224,196,0.16)` | Ambient halo / glow shadow |

### Functional spectrum
Each hue carries consistent meaning across console and decks.
| Token | Hex | Meaning / use |
|-------|-----|---------------|
| **Pulse** | `#7B61FF` | Privacy / differential privacy; secondary accent; gradient partner |
| **Verdant** | `#57E08A` | Carbon / sustainability / healthy & positive |
| **Ion** | `#3FA9FF` | Compute / query / informational |
| **Solar** | `#FFB454` | Equity / access / warnings & attention |
| **Crimson** | `#FF5C72` | Denials / errors / critical alerts |

### Text on Veil
| Token | Hex | Role |
|-------|-----|------|
| **Lumen** | `#EAF1FF` | Primary text, headings |
| Muted | `#93A1C0` | Secondary text |
| Faint | `#5C6B8A` | Tertiary / labels / hints |

**Semantic discipline:** keep the meanings stable — Pulse = privacy, Verdant = carbon, Ion =
compute, Solar = equity, Crimson = error. This is how the KPI cards ([KPIs](../product/kpis.md)) stay
instantly legible.

---

## 4. Logo

**Concept:** an **aperture of three converging arcs** — a camera/lens iris formed by many
blades resolving to one luminous core. It reads as **many domains → one trusted lens**: every
market, focused through a single, dependable platform. The arcs are drawn in the Auralis→Pulse
gradient; the core glows in near-white Auralis. (`brand/logo-mark.svg`,
`brand/logo-wordmark.svg`, `brand/favicon.svg`.)

**Anatomy**
- Three gradient arcs at 120° rotations (the aperture blades = many domains).
- Data nodes at the blade tips (data entering the lens).
- A radiant core (`#EAFFFB` → Auralis → Auralis Deep) — data resolved into trusted knowledge.
- A faint planet ring at 14% Auralis opacity (planet-scale).

**Variants**
- **Mark** — the aperture alone (`logo-mark.svg`), for square/avatar/app contexts.
- **Wordmark** — mark + `AEGORIA` in Inter Tight, tracked caps (`logo-wordmark.svg`).
- **Favicon** — mark on a rounded Veil tile (`favicon.svg`).

**Usage rules**
- Prefer the logo on **Veil** or a dark surface. On light backgrounds, use a dark-tile or
  solid-Auralis lockup; never place the gradient mark on a busy or low-contrast field.
- Maintain clear space ≥ the core's diameter on all sides.
- **Don't** recolour the mark off-palette, stretch/skew it, add drop shadows beyond the
  defined `shadow.glow`, rotate the wordmark, or reconstruct the aperture with a different
  blade count.

---

## 5. Typography

Three open typefaces, mirrored in `brand/tokens.json` → `font`:

| Role | Typeface | Token | Use |
|------|----------|-------|-----|
| **Display** | Inter Tight | `font.display` | Headlines, the wordmark, big stat values |
| **Body** | Inter | `font.body` | UI and prose |
| **Mono** | JetBrains Mono | `font.mono` | Code, SQL, query strings, identifiers, ε/numeric badges |

Guidance
- Use **tabular/`tabular-nums`** for metrics and KPI values so numbers align.
- Display weight ~600, generous tracking on the wordmark (caps). Body stays regular/medium.
- Mono signals "machine truth" — SQL in the governed-query log, dataset ids, ε values.

**Shape language:** rounded but precise. Radii from `brand/tokens.json` → `radius`
(`sm 8 · md 12 · lg 18 · xl 26 · pill 999`). Elevation via `shadow.panel`; signature glow via
`shadow.glow`.

---

## 6. Voice

Aegoria sounds like a **trustworthy systems engineer who cares about people** — precise, calm,
and concrete; never breathless, never opaque.

- **Trustworthy & exact.** Claims are measurable. Say "p95 ≤ 2s at TB-scale" and "ε ≤ 1.0,
  δ = 1e-6", not "blazing fast" or "fully private."
- **Plain over jargon.** Explain the standard, then the benefit. The reader should leave
  understanding *why*, not just *that*.
- **Human stakes.** We name the people the platform serves — excluded orgs, public-interest
  researchers, communities — because the mission is equity, not just throughput.
- **Confident, not hyped.** Let the evidence (KPIs, the two unrelated reference domains) carry
  the weight.

**Vocabulary:** "domain-agnostic / market-agnostic," "the core never changes," "privacy and
sovereignty by default," "data you can trust," "the commons," "one trusted lens." Avoid
"AI-powered" filler, "revolutionary," "military-grade," and other unverifiable hype.

---

## 7. Do / Don't

**Do**
- Use Auralis as the signature accent on a dark Veil canvas; keep it for *signal*.
- Keep the functional hues semantically stable (Pulse = privacy, Verdant = carbon, …).
- Pull exact values from `brand/tokens.json`; let the console (`apps/console`) be the living
  reference implementation.
- Pair every quantitative claim with its definition/target (cross-link [KPIs](../product/kpis.md)).
- Show provenance, lineage, and privacy as first-class — visible trust is the brand.

**Don't**
- Don't flood large areas with solid Auralis or use the Auralis→Pulse gradient as a generic
  background.
- Don't introduce off-palette colours or reassign hue meanings.
- Don't recolour, distort, shadow, or rebuild the logo aperture.
- Don't market in a light theme by default — Aegoria is dark-first.
- Don't overstate guarantees; precision *is* the brand.

---

## 8. Asset reference (`brand/`)

| File | What it is |
|------|------------|
| `brand/tokens.json` | Machine-readable brand tokens — colour, gradient, font, radius, shadow (source of truth) |
| `brand/logo-mark.svg` | The aperture mark |
| `brand/logo-wordmark.svg` | Mark + `AEGORIA` wordmark |
| `brand/favicon.svg` | Mark on a rounded Veil tile |

The console consumes these via `apps/console/tailwind.config.ts` and `app/globals.css`;
treat the running console as the canonical demonstration of the brand in motion.
