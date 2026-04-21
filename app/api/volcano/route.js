import { sql } from '@vercel/postgres';

// 1. THIS IS FOR THE APK (To Pull Data)
export async function GET() {
  const { rows } = await sql`SELECT * FROM "Upload" ORDER BY "createdAt" DESC LIMIT 10`;
  return Response.json(rows);
}

// 2. THIS IS FOR THE EXE (To Push Data)
export async function POST(request) {
  const body = await request.json(); // The EXE sends { "userName": "...", "message": "..." }
  
  await sql`INSERT INTO "Upload" ("userName", "message") 
            VALUES (${body.userName}, ${body.message});`;

  return Response.json({ success: true });
}
