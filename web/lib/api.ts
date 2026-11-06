import type { FinalProofBundle } from "./types";

const configuredBase = process.env.NEXT_PUBLIC_REVERSA_API_URL?.trim();

export const API_BASE = configuredBase ? configuredBase.replace(/\/$/, "") : "";
export const USES_EXTERNAL_PROOF_API = API_BASE.length > 0;

export async function fetchFinalProof(signal?: AbortSignal): Promise<FinalProofBundle> {
  const endpoint = USES_EXTERNAL_PROOF_API
    ? `${API_BASE}/api/proof/final`
    : "/api/proof/final";

  const response = await fetch(endpoint, {
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(
      `Proof source returned HTTP ${response.status}${detail ? `: ${detail.slice(0, 180)}` : ""}`,
    );
  }

  return response.json();
}
