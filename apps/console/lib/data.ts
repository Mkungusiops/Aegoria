/**
 * Console data access. If AEGORIA_API_URL is set, fetches from the control-plane;
 * otherwise returns the built-in fixtures below. Either way, pages call these
 * typed accessors only — never touch transport directly.
 *
 * The fixtures deliberately model TWO UNRELATED DOMAINS — climate-emissions
 * (geospatial / imagery / sensor) and consumer-credit (structured / PII / financial)
 * — to demonstrate that the same platform serves interchangeable markets.
 */

import type {
  AccessPolicy,
  CarbonReading,
  CommonsProposal,
  Dataset,
  DomainPack,
  GraphEntity,
  GraphRelation,
  Kpi,
  LineageEdge,
  LineageNode,
  OverviewMetrics,
  Pipeline,
  PrivacyBudget,
  QueryRun,
} from "./types";

const API = process.env.AEGORIA_API_URL || "";

async function fromApi<T>(path: string, fallback: T): Promise<T> {
  if (!API) return fallback;
  try {
    const res = await fetch(`${API}${path}`, { next: { revalidate: 15 } });
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

/* ----------------------------------------------------------- Domain packs */
export const domainPacks: DomainPack[] = [
  {
    id: "climate-emissions",
    name: "Climate · Emissions & Earth Observation",
    version: "0.4.2",
    description:
      "Facility-level greenhouse-gas emissions fused with satellite imagery and ground IoT sensors. Geospatial + time-series + imagery.",
    maintainer: "Open Climate Commons",
    status: "active",
    modalities: ["geospatial", "imagery", "sensor_stream", "time_series"],
    datasets: 6,
    ontologyTerms: 38,
    qualityRules: 21,
    models: 3,
    policies: 4,
    coreCompat: ">=0.1.0,<1.0.0",
    installedAt: "2026-02-11",
    color: "verdant",
  },
  {
    id: "consumer-credit",
    name: "Finance · Consumer Credit Risk",
    version: "0.3.0",
    description:
      "Loan applications, repayment histories and bureau signals for fair, privacy-preserving credit risk. Structured + PII + financial.",
    maintainer: "Fair Lending Consortium",
    status: "active",
    modalities: ["structured", "time_series"],
    datasets: 5,
    ontologyTerms: 29,
    qualityRules: 27,
    models: 4,
    policies: 6,
    coreCompat: ">=0.1.0,<1.0.0",
    installedAt: "2026-02-18",
    color: "auralis",
  },
  {
    id: "public-health",
    name: "Health · Population Surveillance",
    version: "0.2.1",
    description: "De-identified clinical encounters and syndromic signals under HIPAA with federated learning.",
    maintainer: "Regional Health Network",
    status: "marketplace",
    modalities: ["structured", "time_series", "text"],
    datasets: 7,
    ontologyTerms: 52,
    qualityRules: 33,
    models: 5,
    policies: 9,
    coreCompat: ">=0.1.0,<1.0.0",
    color: "ion",
  },
  {
    id: "freight-logistics",
    name: "Logistics · Multimodal Freight",
    version: "0.1.4",
    description: "Telematics, port events and shipment manifests for resilient supply chains.",
    maintainer: "Global Freight Alliance",
    status: "marketplace",
    modalities: ["event_stream", "geospatial", "structured"],
    datasets: 8,
    ontologyTerms: 41,
    qualityRules: 24,
    models: 2,
    policies: 5,
    coreCompat: ">=0.1.0,<1.0.0",
    color: "solar",
  },
];

/* ---------------------------------------------------------------- Datasets */
export const datasets: Dataset[] = [
  {
    id: "climate-emissions/facility_emissions@0.4.2",
    domain: "climate-emissions",
    name: "facility_emissions",
    title: "Facility GHG Emissions",
    description: "Monthly CO₂e by industrial facility, reconciled against satellite plume detection.",
    modality: "time_series",
    owner: "Open Climate Commons",
    tags: ["emissions", "scope-1", "ghg", "facility"],
    jurisdiction: "GLOBAL",
    regulations: ["CSRD"],
    residencyRequired: false,
    license: "CC-BY-4.0",
    rows: 48_200_000,
    bytes: 7_900_000_000,
    qualityScore: 0.97,
    fair: { findable: true, accessible: true, interoperable: true, reusable: true },
    fields: [
      { name: "facility_id", type: "string", sensitivity: "public", pii: false, semanticType: "emissions:Facility" },
      { name: "geom", type: "geometry", sensitivity: "public", pii: false, semanticType: "geo:Point" },
      { name: "co2e_tonnes", type: "double", sensitivity: "public", pii: false, semanticType: "emissions:CO2e", description: "tonnes CO₂-equivalent" },
      { name: "observed_at", type: "timestamp", sensitivity: "public", pii: false },
      { name: "operator", type: "string", sensitivity: "internal", pii: false },
    ],
    updatedAt: "2026-06-16T04:12:00Z",
    signed: true,
    piiFields: 0,
  },
  {
    id: "climate-emissions/sentinel_plumes@0.4.2",
    domain: "climate-emissions",
    name: "sentinel_plumes",
    title: "Satellite Plume Detections",
    description: "Methane/CO₂ plume detections derived from Sentinel-5P imagery tiles.",
    modality: "imagery",
    owner: "Open Climate Commons",
    tags: ["satellite", "methane", "imagery", "sentinel"],
    jurisdiction: "EU",
    regulations: ["INSPIRE"],
    residencyRequired: false,
    license: "CC-BY-4.0",
    rows: 12_400_000,
    bytes: 41_000_000_000,
    qualityScore: 0.93,
    fair: { findable: true, accessible: true, interoperable: true, reusable: true },
    fields: [
      { name: "tile_id", type: "string", sensitivity: "public", pii: false },
      { name: "geom", type: "geometry", sensitivity: "public", pii: false, semanticType: "geo:Polygon" },
      { name: "ch4_ppb", type: "double", sensitivity: "public", pii: false },
      { name: "captured_at", type: "timestamp", sensitivity: "public", pii: false },
    ],
    updatedAt: "2026-06-17T01:30:00Z",
    signed: true,
    piiFields: 0,
  },
  {
    id: "climate-emissions/ground_sensors@0.4.2",
    domain: "climate-emissions",
    name: "ground_sensors",
    title: "Ground IoT Air-Quality Stream",
    description: "Real-time PM2.5 / CO₂ readings from a mesh of municipal sensors.",
    modality: "sensor_stream",
    owner: "City Sensor Networks",
    tags: ["iot", "air-quality", "realtime"],
    jurisdiction: "US",
    regulations: [],
    residencyRequired: false,
    license: "ODbL-1.0",
    rows: 920_000_000,
    bytes: 18_000_000_000,
    qualityScore: 0.9,
    fair: { findable: true, accessible: true, interoperable: true, reusable: true },
    fields: [
      { name: "sensor_id", type: "string", sensitivity: "public", pii: false },
      { name: "pm25", type: "float", sensitivity: "public", pii: false },
      { name: "co2_ppm", type: "float", sensitivity: "public", pii: false },
      { name: "ts", type: "timestamp", sensitivity: "public", pii: false },
    ],
    updatedAt: "2026-06-17T02:05:00Z",
    signed: false,
    piiFields: 0,
  },
  {
    id: "consumer-credit/loan_applications@0.3.0",
    domain: "consumer-credit",
    name: "loan_applications",
    title: "Loan Applications",
    description: "Consumer loan applications with applicant attributes and decisions.",
    modality: "structured",
    owner: "Fair Lending Consortium",
    tags: ["credit", "loan", "underwriting"],
    jurisdiction: "EU",
    regulations: ["GDPR", "ECOA"],
    residencyRequired: true,
    license: "Proprietary-Restricted",
    rows: 6_300_000,
    bytes: 2_100_000_000,
    qualityScore: 0.95,
    fair: { findable: true, accessible: true, interoperable: true, reusable: false },
    fields: [
      { name: "application_id", type: "string", sensitivity: "internal", pii: false },
      { name: "applicant_name", type: "string", sensitivity: "pii", pii: true, semanticType: "fibo:PartyName" },
      { name: "national_id", type: "string", sensitivity: "pii", pii: true },
      { name: "email", type: "string", sensitivity: "pii", pii: true },
      { name: "income", type: "double", sensitivity: "financial", pii: false, semanticType: "fibo:Income" },
      { name: "amount", type: "double", sensitivity: "financial", pii: false },
      { name: "decision", type: "string", sensitivity: "confidential", pii: false },
    ],
    updatedAt: "2026-06-16T22:40:00Z",
    signed: true,
    piiFields: 3,
  },
  {
    id: "consumer-credit/repayment_history@0.3.0",
    domain: "consumer-credit",
    name: "repayment_history",
    title: "Repayment History",
    description: "Monthly repayment performance per account, used for risk modelling.",
    modality: "time_series",
    owner: "Fair Lending Consortium",
    tags: ["credit", "repayment", "delinquency"],
    jurisdiction: "EU",
    regulations: ["GDPR"],
    residencyRequired: true,
    license: "Proprietary-Restricted",
    rows: 88_000_000,
    bytes: 5_400_000_000,
    qualityScore: 0.96,
    fair: { findable: true, accessible: true, interoperable: true, reusable: false },
    fields: [
      { name: "account_id", type: "string", sensitivity: "internal", pii: false },
      { name: "month", type: "date", sensitivity: "internal", pii: false },
      { name: "balance", type: "double", sensitivity: "financial", pii: false },
      { name: "days_past_due", type: "int", sensitivity: "confidential", pii: false },
    ],
    updatedAt: "2026-06-15T18:00:00Z",
    signed: true,
    piiFields: 0,
  },
];

/* ----------------------------------------------------------- Lineage graph */
export const lineageNodes: LineageNode[] = [
  { id: "src:sentinel5p", label: "Sentinel-5P", kind: "source", domain: "climate-emissions" },
  { id: "src:iot-mesh", label: "City IoT Mesh", kind: "stream", domain: "climate-emissions" },
  { id: "climate-emissions/sentinel_plumes", label: "sentinel_plumes", kind: "dataset", domain: "climate-emissions" },
  { id: "climate-emissions/ground_sensors", label: "ground_sensors", kind: "dataset", domain: "climate-emissions" },
  { id: "climate-emissions/facility_emissions", label: "facility_emissions", kind: "dataset", domain: "climate-emissions" },
  { id: "model:plume-fusion", label: "Plume Fusion v2", kind: "model", domain: "climate-emissions" },
  { id: "product:emissions-index", label: "Regional Emissions Index", kind: "product", domain: "climate-emissions" },
  { id: "src:bureau", label: "Credit Bureau Feed", kind: "source", domain: "consumer-credit" },
  { id: "consumer-credit/loan_applications", label: "loan_applications", kind: "dataset", domain: "consumer-credit" },
  { id: "consumer-credit/repayment_history", label: "repayment_history", kind: "dataset", domain: "consumer-credit" },
  { id: "model:risk-scorer", label: "Fair Risk Scorer", kind: "model", domain: "consumer-credit" },
  { id: "product:risk-api", label: "Credit Decision API", kind: "product", domain: "consumer-credit" },
];
export const lineageEdges: LineageEdge[] = [
  { from: "src:sentinel5p", to: "climate-emissions/sentinel_plumes", operation: "ingest" },
  { from: "src:iot-mesh", to: "climate-emissions/ground_sensors", operation: "stream" },
  { from: "climate-emissions/sentinel_plumes", to: "model:plume-fusion", operation: "train" },
  { from: "climate-emissions/ground_sensors", to: "model:plume-fusion", operation: "train" },
  { from: "model:plume-fusion", to: "climate-emissions/facility_emissions", operation: "infer" },
  { from: "climate-emissions/facility_emissions", to: "product:emissions-index", operation: "publish" },
  { from: "src:bureau", to: "consumer-credit/loan_applications", operation: "ingest" },
  { from: "consumer-credit/loan_applications", to: "model:risk-scorer", operation: "train" },
  { from: "consumer-credit/repayment_history", to: "model:risk-scorer", operation: "train" },
  { from: "model:risk-scorer", to: "product:risk-api", operation: "publish" },
];

/* -------------------------------------------------------------- Policies */
export const policies: AccessPolicy[] = [
  {
    id: "cc-dp-aggregate",
    description: "Analysts may only query loan data in aggregate, with differential privacy.",
    effect: "allow",
    roles: ["analyst", "researcher"],
    actions: ["query", "aggregate"],
    datasets: ["consumer-credit/*"],
    condition: "principal.clearance >= confidential",
    obligations: ["differential_privacy(ε=1.0)", "aggregate_only"],
    domain: "consumer-credit",
  },
  {
    id: "cc-pii-mask",
    description: "Mask applicant PII for everyone except the owning institution.",
    effect: "allow",
    roles: ["*"],
    actions: ["read", "query"],
    datasets: ["consumer-credit/loan_applications"],
    condition: "resource.owner != principal.org",
    obligations: ["mask(applicant_name, national_id, email)"],
    domain: "consumer-credit",
  },
  {
    id: "cc-residency-eu",
    description: "EU credit data may not be processed outside EU regions.",
    effect: "deny",
    roles: ["*"],
    actions: ["query", "export", "train"],
    datasets: ["consumer-credit/*"],
    condition: "compute.region not in EU",
    obligations: ["residency(EU)"],
    domain: "consumer-credit",
  },
  {
    id: "ce-open-access",
    description: "Emissions data is openly queryable by any authenticated principal.",
    effect: "allow",
    roles: ["*"],
    actions: ["read", "query", "aggregate", "export"],
    datasets: ["climate-emissions/*"],
    obligations: ["watermark"],
    domain: "climate-emissions",
  },
];

/* ------------------------------------------------------------ Privacy budgets */
export const privacyBudgets: PrivacyBudget[] = [
  { subject: "analyst@riskco", dataset: "consumer-credit/loan_applications", epsilon: 4.0, spent: 2.6 },
  { subject: "research@univ", dataset: "consumer-credit/repayment_history", epsilon: 2.0, spent: 0.4 },
  { subject: "ngo@climate", dataset: "climate-emissions/facility_emissions", epsilon: 8.0, spent: 1.2 },
];

/* ----------------------------------------------------------------- Carbon */
export const carbonReadings: CarbonReading[] = [
  { region: "eu-north", gco2PerKwh: 28, renewableFraction: 0.94 },
  { region: "us-west", gco2PerKwh: 210, renewableFraction: 0.41 },
  { region: "local", gco2PerKwh: 380, renewableFraction: 0.22 },
  { region: "ap-south", gco2PerKwh: 640, renewableFraction: 0.12 },
];

/* ------------------------------------------------------------------ Queries */
export const queryRuns: QueryRun[] = [
  {
    id: "q-8821",
    sql: "SELECT region, SUM(co2e_tonnes) FROM facility_emissions GROUP BY region",
    principal: "ngo@climate",
    domain: "climate-emissions",
    engine: "duckdb",
    region: "eu-north",
    rows: 142,
    bytesScanned: 410_000_000,
    durationMs: 380,
    carbonG: 0.42,
    dpApplied: false,
    epsilonSpent: 0,
    at: "2026-06-17T02:51:00Z",
    status: "ok",
  },
  {
    id: "q-8822",
    sql: "SELECT AVG(income) FROM loan_applications WHERE decision='approved'",
    principal: "analyst@riskco",
    domain: "consumer-credit",
    engine: "duckdb",
    region: "eu-north",
    rows: 1,
    bytesScanned: 88_000_000,
    durationMs: 210,
    carbonG: 0.11,
    dpApplied: true,
    epsilonSpent: 0.4,
    at: "2026-06-17T02:55:00Z",
    status: "ok",
  },
  {
    id: "q-8823",
    sql: "SELECT applicant_name, national_id FROM loan_applications LIMIT 100",
    principal: "analyst@riskco",
    domain: "consumer-credit",
    engine: "—",
    region: "—",
    rows: 0,
    bytesScanned: 0,
    durationMs: 4,
    carbonG: 0,
    dpApplied: false,
    epsilonSpent: 0,
    at: "2026-06-17T02:58:00Z",
    status: "denied",
  },
];

/* ---------------------------------------------------------------- Pipelines */
export const pipelines: Pipeline[] = [
  {
    id: "pl-ce-sentinel",
    name: "Sentinel-5P Tile Ingest",
    domain: "climate-emissions",
    modality: "imagery",
    schedule: "*/15 * * * *",
    status: "healthy",
    lastRun: "2026-06-17T02:45:00Z",
    recordsPerMin: 12400,
    freshnessSec: 540,
    throughput: [8, 11, 9, 14, 12, 13, 12, 15, 14, 12],
  },
  {
    id: "pl-ce-iot",
    name: "City IoT Sensor Stream",
    domain: "climate-emissions",
    modality: "sensor_stream",
    schedule: "streaming",
    status: "running",
    lastRun: "2026-06-17T03:00:00Z",
    recordsPerMin: 88000,
    freshnessSec: 3,
    throughput: [70, 82, 78, 90, 88, 84, 92, 88, 86, 88],
  },
  {
    id: "pl-cc-bureau",
    name: "Credit Bureau Nightly",
    domain: "consumer-credit",
    modality: "structured",
    schedule: "0 2 * * *",
    status: "healthy",
    lastRun: "2026-06-17T02:00:00Z",
    recordsPerMin: 5200,
    freshnessSec: 3600,
    throughput: [5, 6, 5, 7, 6, 5, 6, 6, 5, 6],
  },
  {
    id: "pl-cc-repay",
    name: "Repayment Reconciliation",
    domain: "consumer-credit",
    modality: "time_series",
    schedule: "0 4 * * *",
    status: "degraded",
    lastRun: "2026-06-17T04:00:00Z",
    recordsPerMin: 2100,
    freshnessSec: 7200,
    throughput: [3, 2, 3, 1, 2, 3, 2, 1, 2, 2],
  },
];

/* ------------------------------------------------------------ Knowledge graph */
export const graphEntities: GraphEntity[] = [
  { id: "fac:steelworks-12", label: "Steelworks 12", type: "Facility", domain: "climate-emissions", x: 0.2, y: 0.3 },
  { id: "region:ruhr", label: "Ruhr Region", type: "Region", domain: "climate-emissions", x: 0.42, y: 0.18 },
  { id: "op:acme-metals", label: "Acme Metals", type: "Operator", domain: "climate-emissions", x: 0.2, y: 0.62 },
  { id: "org:acme-financial", label: "Acme Financial", type: "Institution", domain: "consumer-credit", x: 0.62, y: 0.62 },
  { id: "borrower:42", label: "Borrower #42", type: "Borrower", domain: "consumer-credit", x: 0.82, y: 0.4 },
  { id: "region:eu", label: "European Union", type: "Jurisdiction", domain: "shared", x: 0.52, y: 0.4 },
];
export const graphRelations: GraphRelation[] = [
  { from: "fac:steelworks-12", to: "region:ruhr", type: "located_in" },
  { from: "fac:steelworks-12", to: "op:acme-metals", type: "operated_by" },
  { from: "op:acme-metals", to: "org:acme-financial", type: "same_corporate_group" },
  { from: "borrower:42", to: "org:acme-financial", type: "borrows_from" },
  { from: "region:ruhr", to: "region:eu", type: "within" },
  { from: "org:acme-financial", to: "region:eu", type: "regulated_in" },
];

/* ----------------------------------------------------------- Commons proposals */
export const proposals: CommonsProposal[] = [
  {
    id: "prop-014",
    title: "Open methane plume tiles to all relief agencies",
    summary: "Grant no-cost query access to verified humanitarian responders during climate emergencies.",
    proposer: "Open Climate Commons",
    status: "open",
    forPct: 78,
    participants: 41,
    closesIn: "3 days",
  },
  {
    id: "prop-013",
    title: "Raise default differential-privacy ε floor to 0.8",
    summary: "Strengthen the platform-wide privacy default for all PII-bearing datasets.",
    proposer: "Fair Lending Consortium",
    status: "open",
    forPct: 64,
    participants: 53,
    closesIn: "6 days",
  },
  {
    id: "prop-012",
    title: "Adopt C2PA signing as mandatory for published data products",
    summary: "Every data product must ship a verifiable content-provenance manifest.",
    proposer: "Governance Council",
    status: "passed",
    forPct: 91,
    participants: 67,
    closesIn: "closed",
  },
];

/* --------------------------------------------------------------------- KPIs */
export const kpis: Kpi[] = [
  { id: "lineage", label: "Lineage coverage", value: "98.2%", target: "≥ 95%", progress: 98, tone: "auralis", hint: "datasets with full upstream lineage" },
  { id: "quality", label: "Data quality", value: "0.95", target: "≥ 0.90", progress: 95, tone: "verdant", hint: "avg passing quality rules" },
  { id: "latency", label: "Query latency p95", value: "0.9s", target: "≤ 2s @ TB-scale", progress: 88, tone: "ion", hint: "across all engines" },
  { id: "privacy", label: "Privacy guarantee", value: "ε ≤ 1.0", target: "(ε,δ)-DP default", progress: 100, tone: "pulse", hint: "δ = 1e-6 on PII" },
  { id: "carbon", label: "Carbon / query", value: "0.31g", target: "↓ 60% vs naive", progress: 72, tone: "verdant", hint: "carbon-aware placement" },
  { id: "onboard", label: "New-domain onboarding", value: "2.5 days", target: "≤ 5 days", progress: 80, tone: "auralis", hint: "manifest → live, no core change" },
  { id: "orgs", label: "Orgs empowered", value: "37", target: "↑ excluded sectors", progress: 62, tone: "solar", hint: "12 previously data-poor" },
  { id: "sectors", label: "Sectors live", value: "4", target: "market-agnostic", progress: 50, tone: "pulse", hint: "climate · finance · health · logistics" },
];

/* ----------------------------------------------------------------- Overview */
export const overview: OverviewMetrics = {
  datasets: 26,
  domains: 4,
  rowsIndexed: 1_182_000_000,
  lineageCoverage: 0.982,
  qualityAvg: 0.95,
  carbonPerQuery: 0.31,
  carbonSaved: 0.61,
  privacyEpsilonAvg: 0.92,
  piiProtected: 3,
  orgsOnboarded: 37,
  sectorsOnboarded: 4,
  queriesToday: 18420,
  greenestRegion: "eu-north",
  ingestSeries: [42, 51, 48, 63, 58, 72, 69, 81, 77, 88, 84, 96],
  carbonSeries: [0.9, 0.82, 0.74, 0.68, 0.55, 0.49, 0.44, 0.4, 0.36, 0.34, 0.32, 0.31],
  queryLatencyP95: 0.9,
};

/* ---------------------------------------------------------------- Accessors */
export const getOverview = () => fromApi<OverviewMetrics>("/overview", overview);
export const getDatasets = () => fromApi<Dataset[]>("/datasets", datasets);
export const getDataset = async (id: string) => (await getDatasets()).find((d) => d.id === id || d.id.startsWith(id));
export const getDomainPacks = () => fromApi<DomainPack[]>("/packs", domainPacks);
export const getLineage = () => fromApi<{ nodes: LineageNode[]; edges: LineageEdge[] }>("/lineage", { nodes: lineageNodes, edges: lineageEdges });
export const getPolicies = () => fromApi<AccessPolicy[]>("/policies", policies);
export const getPrivacyBudgets = () => fromApi<PrivacyBudget[]>("/privacy/budgets", privacyBudgets);
export const getCarbon = () => fromApi<CarbonReading[]>("/carbon", carbonReadings);
export const getQueryRuns = () => fromApi<QueryRun[]>("/queries", queryRuns);
export const getPipelines = () => fromApi<Pipeline[]>("/pipelines", pipelines);
export const getGraph = () => fromApi<{ entities: GraphEntity[]; relations: GraphRelation[] }>("/graph", { entities: graphEntities, relations: graphRelations });
export const getProposals = () => fromApi<CommonsProposal[]>("/governance/proposals", proposals);
export const getKpis = () => fromApi<Kpi[]>("/kpis", kpis);

export const fmtNum = (n: number) => {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return `${n}`;
};
export const fmtBytes = (n: number) => {
  if (n >= 1e12) return `${(n / 1e12).toFixed(1)} TB`;
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)} GB`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)} MB`;
  return `${(n / 1e3).toFixed(1)} KB`;
};
