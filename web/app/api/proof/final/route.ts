import { NextResponse } from "next/server";
import snapshot from "@/data/locked-proof/final.json";
import manifest from "@/data/locked-proof/manifest.json";

export const dynamic = "force-static";

export async function GET() {
  if (!("summary" in snapshot) || manifest.generated !== true) {
    return NextResponse.json(
      {
        detail:
          "Hosted proof snapshot is not generated. Run `npm run proof:sync` locally, commit web/data/locked-proof, then redeploy.",
      },
      { status: 503 },
    );
  }

  return NextResponse.json(snapshot, {
    headers: {
      "X-Reversa-Mode": "LOCKED_PROOF_SNAPSHOT",
      "X-Reversa-Snapshot-Sha256": manifest.snapshot_sha256,
      "Cache-Control": "public, max-age=0, s-maxage=31536000, immutable",
    },
  });
}
