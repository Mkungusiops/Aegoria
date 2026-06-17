/**
 * Console-side view models. These mirror the engine's contracts (aegoria_core)
 * but are shaped for presentation. When AEGORIA_API_URL is set, lib/data.ts maps
 * the control-plane responses into these shapes; otherwise it serves fixtures.
 */

export type Modality =
  | "structured"
  | "time_series"
  | "geospatial"
  | "imagery"
  | "sensor_stream"
  | "event_stream"
  | "text";

export type Sensitivity = "public" | "internal" | "confidential" | "pii" | "phi" | "financial" | "restricted";

export interface FairFlags {
  findable: boolean;
  accessible: boolean;
  interoperable: boolean;
  reusable: boolean;
}

export interface Field {
  name: string;
  type: string;
  sensitivity: Sensitivity;
  pii: boolean;
  semanticType?: string;
  description?: string;
}

export interface Dataset {
  id: string;
  domain: string;
  name: string;
  title: string;
  description: string;
  modality: Modality;
  owner: string;
  tags: string[];
  jurisdiction: string;
  regulations: string[];
  residencyRequired: boolean;
  license: string;
  rows: number;
  bytes: number;
  qualityScore: number; // 0..1
  fair: FairFlags;
  fields: Field[];
  updatedAt: string;
  signed: boolean; // C2PA provenance attached
  piiFields: number;
}

export interface DomainPack {
  id: string;
  name: string;
  version: string;
  description: string;
  maintainer: string;
  status: "active" | "draft" | "marketplace";
  modalities: Modality[];
  datasets: number;
  ontologyTerms: number;
  qualityRules: number;
  models: number;
  policies: number;
  coreCompat: string;
  installedAt?: string;
  color: "auralis" | "pulse" | "verdant" | "ion" | "solar";
}

export interface LineageNode {
  id: string;
  label: string;
  kind: "source" | "dataset" | "model" | "product" | "stream";
  domain: string;
}
export interface LineageEdge {
  from: string;
  to: string;
  operation: string;
}

export interface AccessPolicy {
  id: string;
  description: string;
  effect: "allow" | "deny";
  roles: string[];
  actions: string[];
  datasets: string[];
  condition?: string;
  obligations: string[];
  domain: string;
}

export interface PrivacyBudget {
  subject: string;
  dataset: string;
  epsilon: number;
  spent: number;
}

export interface CarbonReading {
  region: string;
  gco2PerKwh: number;
  renewableFraction: number;
}

export interface QueryRun {
  id: string;
  sql: string;
  principal: string;
  domain: string;
  engine: string;
  region: string;
  rows: number;
  bytesScanned: number;
  durationMs: number;
  carbonG: number;
  dpApplied: boolean;
  epsilonSpent: number;
  at: string;
  status: "ok" | "denied" | "running";
}

export interface Pipeline {
  id: string;
  name: string;
  domain: string;
  modality: Modality;
  schedule: string;
  status: "healthy" | "running" | "degraded" | "failed";
  lastRun: string;
  recordsPerMin: number;
  freshnessSec: number;
  throughput: number[]; // sparkline
}

export interface GraphEntity {
  id: string;
  label: string;
  type: string;
  domain: string;
  x: number;
  y: number;
}
export interface GraphRelation {
  from: string;
  to: string;
  type: string;
}

export interface CommonsProposal {
  id: string;
  title: string;
  summary: string;
  proposer: string;
  status: "open" | "passed" | "rejected";
  forPct: number;
  participants: number;
  closesIn: string;
}

export interface Kpi {
  id: string;
  label: string;
  value: string;
  target: string;
  progress: number; // 0..100
  tone: "auralis" | "pulse" | "verdant" | "ion" | "solar" | "crimson";
  hint: string;
}

export interface OverviewMetrics {
  datasets: number;
  domains: number;
  rowsIndexed: number;
  lineageCoverage: number; // 0..1
  qualityAvg: number; // 0..1
  carbonPerQuery: number; // gCO2
  carbonSaved: number; // pct vs naive placement
  privacyEpsilonAvg: number;
  piiProtected: number;
  orgsOnboarded: number;
  sectorsOnboarded: number;
  queriesToday: number;
  greenestRegion: string;
  ingestSeries: number[];
  carbonSeries: number[];
  queryLatencyP95: number;
}
