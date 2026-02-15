import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params;
    const data = await req.json();
    const sql = getDb();

    await sql.query(
      `INSERT INTO style_profiles (user_id, brands, price_range, style_tags, size_info)
       VALUES ($1::uuid, $2, $3::jsonb, $4, $5::jsonb)
       ON CONFLICT (user_id)
       DO UPDATE SET
         brands = EXCLUDED.brands,
         price_range = EXCLUDED.price_range,
         style_tags = EXCLUDED.style_tags,
         size_info = EXCLUDED.size_info`,
      [
        userId,
        data.favorite_brands || [],
        JSON.stringify(data.price_range || {}),
        data.style_preferences || [],
        JSON.stringify(data.size_info || {}),
      ]
    );

    return NextResponse.json({ status: "success", message: "Onboarding completed" });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to save onboarding";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
