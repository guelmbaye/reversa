import { NextResponse } from "next/server";
import manifest from "@/data/locked-proof/manifest.json";

export const dynamic = "force-static";

export async function GET() {
  return NextResponse.json({
    status: manifest.generated === true ? "ok" : "not_ready",
    mode: "HOSTED_VERIFIED_PROOF",
    snapshot_generated: manifest.generated === true,
    snapshot_sha256: manifest.generated === true ? manifest.snapshot_sha256 : null,
    gate_result: manifest.generated === true ? manifest.gate_result : null,
  });
}
