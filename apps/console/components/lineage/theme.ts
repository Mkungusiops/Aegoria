/**
 * Visual vocabulary for lineage rendering — kept out of the React tree so the
 * DAG component and the side panel agree on colours and labels.
 */

import type { LineageNode } from "@/lib/types";
import type { Tone } from "@/components/ui/primitives";

export const NODE_COLORS = {
  auralis: "#16E0C4",
  pulse: "#7B61FF",
  verdant: "#57E08A",
  ion: "#3FA9FF",
  solar: "#FFB454",
  crimson: "#FF5C72",
  muted: "#93A1C0",
} as const;

/** Each lineage stage gets a stable colour so the pipeline reads at a glance. */
export const KIND_META: Record<
  LineageNode["kind"],
  { label: string; color: keyof typeof NODE_COLORS; tone: Tone; glyph: string }
> = {
  source: { label: "Source", color: "ion", tone: "ion", glyph: "◈" },
  stream: { label: "Stream", color: "solar", tone: "solar", glyph: "≋" },
  dataset: { label: "Dataset", color: "auralis", tone: "auralis", glyph: "▦" },
  model: { label: "Model", color: "pulse", tone: "pulse", glyph: "✦" },
  product: { label: "Product", color: "verdant", tone: "verdant", glyph: "★" },
};

/** Operation styling for edge labels. */
export const OP_META: Record<string, { tone: Tone; color: keyof typeof NODE_COLORS }> = {
  ingest: { tone: "ion", color: "ion" },
  stream: { tone: "solar", color: "solar" },
  train: { tone: "pulse", color: "pulse" },
  infer: { tone: "auralis", color: "auralis" },
  publish: { tone: "verdant", color: "verdant" },
};

export function opMeta(op: string) {
  return OP_META[op] ?? { tone: "neutral" as Tone, color: "muted" as const };
}

/** Domain accent — the stripe that makes two lineages visibly independent. */
export const DOMAIN_META: Record<string, { label: string; color: keyof typeof NODE_COLORS }> = {
  "climate-emissions": { label: "Climate · Emissions", color: "verdant" },
  "consumer-credit": { label: "Finance · Credit", color: "auralis" },
  shared: { label: "Shared", color: "pulse" },
};

export function domainMeta(domain: string) {
  return DOMAIN_META[domain] ?? { label: domain, color: "muted" as const };
}

/**
 * Synthetic-but-realistic provenance for each lineage node. The platform attaches
 * a C2PA-style signed manifest, content checksum and capture time to every
 * artifact; the engine would source these from the ProvenanceSigner adapter.
 */
export interface Provenance {
  signed: boolean;
  signer: string;
  algorithm: string;
  checksum: string;
  capturedAt: string;
  manifest: string;
}

export const PROVENANCE: Record<string, Provenance> = {
  "src:sentinel5p": {
    signed: true,
    signer: "ESA Copernicus Ground Segment",
    algorithm: "Ed25519 · C2PA 1.3",
    checksum: "blake3:4f1a…c0e2",
    capturedAt: "2026-06-17T00:50:00Z",
    manifest: "urn:c2pa:sentinel5p:L2-CH4:2026-06-17",
  },
  "src:iot-mesh": {
    signed: true,
    signer: "City Sensor Networks Edge CA",
    algorithm: "Ed25519 · device attestation",
    checksum: "blake3:9b22…7d41",
    capturedAt: "2026-06-17T03:00:00Z",
    manifest: "urn:c2pa:iot-mesh:stream:2026-06-17T03",
  },
  "climate-emissions/sentinel_plumes": {
    signed: true,
    signer: "Aegoria Ingest · ed25519",
    algorithm: "Ed25519 · C2PA 1.3",
    checksum: "blake3:1c8d…aa90",
    capturedAt: "2026-06-17T01:30:00Z",
    manifest: "urn:c2pa:aegoria:sentinel_plumes@0.4.2",
  },
  "climate-emissions/ground_sensors": {
    signed: false,
    signer: "—",
    algorithm: "unsigned · streaming",
    checksum: "blake3:6e30…12fb",
    capturedAt: "2026-06-17T02:05:00Z",
    manifest: "—",
  },
  "climate-emissions/facility_emissions": {
    signed: true,
    signer: "Aegoria Ingest · ed25519",
    algorithm: "Ed25519 · C2PA 1.3",
    checksum: "blake3:b740…55c1",
    capturedAt: "2026-06-16T04:12:00Z",
    manifest: "urn:c2pa:aegoria:facility_emissions@0.4.2",
  },
  "model:plume-fusion": {
    signed: true,
    signer: "Aegoria MLService · model-card",
    algorithm: "Ed25519 · model attestation",
    checksum: "blake3:2af9…e8b3",
    capturedAt: "2026-06-15T09:00:00Z",
    manifest: "urn:c2pa:aegoria:plume-fusion@2.0",
  },
  "product:emissions-index": {
    signed: true,
    signer: "Aegoria ProvenanceService",
    algorithm: "Ed25519 · C2PA 1.3",
    checksum: "blake3:7d11…04ae",
    capturedAt: "2026-06-17T02:40:00Z",
    manifest: "urn:c2pa:aegoria:emissions-index:release",
  },
  "src:bureau": {
    signed: true,
    signer: "Credit Bureau Mutual TLS",
    algorithm: "Ed25519 · sealed feed",
    checksum: "blake3:f0a2…9c77",
    capturedAt: "2026-06-17T02:00:00Z",
    manifest: "urn:c2pa:bureau:nightly:2026-06-17",
  },
  "consumer-credit/loan_applications": {
    signed: true,
    signer: "Aegoria Ingest · ed25519",
    algorithm: "Ed25519 · C2PA 1.3",
    checksum: "blake3:3bd8…71a0",
    capturedAt: "2026-06-16T22:40:00Z",
    manifest: "urn:c2pa:aegoria:loan_applications@0.3.0",
  },
  "consumer-credit/repayment_history": {
    signed: true,
    signer: "Aegoria Ingest · ed25519",
    algorithm: "Ed25519 · C2PA 1.3",
    checksum: "blake3:88c4…2de5",
    capturedAt: "2026-06-15T18:00:00Z",
    manifest: "urn:c2pa:aegoria:repayment_history@0.3.0",
  },
  "model:risk-scorer": {
    signed: true,
    signer: "Aegoria MLService · model-card",
    algorithm: "Ed25519 · model attestation",
    checksum: "blake3:5ee1…b6c9",
    capturedAt: "2026-06-14T11:30:00Z",
    manifest: "urn:c2pa:aegoria:risk-scorer@1.4 · fairness-audited",
  },
  "product:risk-api": {
    signed: true,
    signer: "Aegoria ProvenanceService",
    algorithm: "Ed25519 · C2PA 1.3",
    checksum: "blake3:a902…ff31",
    capturedAt: "2026-06-17T01:15:00Z",
    manifest: "urn:c2pa:aegoria:risk-api:release",
  },
};

export function provenanceFor(id: string): Provenance {
  return (
    PROVENANCE[id] ?? {
      signed: false,
      signer: "—",
      algorithm: "—",
      checksum: "—",
      capturedAt: "—",
      manifest: "—",
    }
  );
}
