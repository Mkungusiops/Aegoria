import type { QueryRun } from "@/lib/types";

/**
 * Presentation-only enrichment of stored query runs. The governance receipt is
 * driven entirely by the QueryRun fixture; this module adds the tabular result
 * preview and the masked-column list that the engine's governance service would
 * have produced, so Query Studio can render a faithful end-to-end picture
 * without a live backend.
 */

export interface ResultTable {
  columns: string[];
  rows: (string | number)[][];
}

export interface QueryExample extends QueryRun {
  title: string;
  result: ResultTable | null;
  /** Columns the governance layer masked or suppressed before returning rows. */
  maskedColumns: string[];
  /** Human-readable authorization rationale shown on the receipt. */
  authorization: string;
}

/** Build the enriched example list from the canonical query runs. */
export function buildExamples(runs: QueryRun[]): QueryExample[] {
  return runs.map((run) => {
    const meta = ENRICHMENT[run.id] ?? FALLBACK;
    return { ...run, ...meta };
  });
}

const FALLBACK: Omit<QueryExample, keyof QueryRun> = {
  title: "Governed query",
  result: null,
  maskedColumns: [],
  authorization: "Authorized by default policy.",
};

const ENRICHMENT: Record<string, Omit<QueryExample, keyof QueryRun>> = {
  "q-8821": {
    title: "Regional emissions rollup",
    authorization: "Allowed by ce-open-access — emissions data is openly queryable by any authenticated principal.",
    maskedColumns: [],
    result: {
      columns: ["region", "sum_co2e_tonnes"],
      rows: [
        ["eu-north", 1_284_900],
        ["us-west", 3_910_440],
        ["ap-south", 5_602_118],
        ["sa-east", 842_007],
        ["af-west", 318_550],
      ],
    },
  },
  "q-8822": {
    title: "Approved-applicant income (DP)",
    authorization: "Allowed by cc-dp-aggregate — aggregate-only with (ε,δ)-differential privacy for analysts.",
    maskedColumns: [],
    result: {
      columns: ["avg_income"],
      // Differentially-private aggregate; noise applied at ε = 0.4.
      rows: [[61_842.37]],
    },
  },
  "q-8823": {
    title: "Raw PII select (denied)",
    authorization:
      "Denied by cc-pii-mask — row-level PII (applicant_name, national_id) cannot be selected outside the owning institution.",
    maskedColumns: ["applicant_name", "national_id"],
    result: null,
  },
};

/** Tiny example library for the "Examples" chooser — keyed to the same runs. */
export const EXAMPLE_LIBRARY: { id: string; label: string }[] = [
  { id: "q-8821", label: "Emissions by region" },
  { id: "q-8822", label: "DP income average" },
  { id: "q-8823", label: "Blocked PII select" },
];
