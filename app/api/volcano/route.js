javascript
import { sql } from '@vercel/postgres';

// THE PULL (For the APK)
export async function GET() {
try {
const { rows } = await sqlSELECT * FROM "Upload" ORDER BY "createdAt" DESC LIMIT 20;
return Response.json(rows, { status: 200 });
} catch (error) {
return Response.json({ error: error.message }, { status: 500 });
}
}

// THE PUSH (For the Windows EXE)
export async function POST(request) {
try {
const body = await request.json();
const { userName, message } = body;

await sql`INSERT INTO "Upload" ("userName", "message") VALUES (${userName}, ${message});`;

return Response.json({ success: "Data Pushed!" }, { status: 200 });
} catch (error) {
return Response.json({ error: error.message }, { status: 500 });
}
}
