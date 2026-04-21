import { sql } from '@vercel/postgres';

export async function GET() {
  try {
    // Pulls everything for your HTML Dashboard and APK
    const { rows } = await sql`SELECT * FROM "Upload" ORDER BY "createdAt" DESC LIMIT 50`;
    return Response.json(rows, { status: 200 });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const raw = await request.text();
    const p = raw.split(',');

    // Mapping segments: distance, vibration, seismic, dist_alert, seis_alert, dual_alert, kill, sys, min_u, min_s
    const data = {
      dist:  parseFloat(p[0]) || 0,
      vib:   parseInt(p[1]) || 0,
      seis:  parseInt(p[2]) || 0,
      dA:    p[3]?.trim() === 'DIST_ALERT',
      sA:    p[4]?.trim() === 'SEIS_ALERT',
      duA:   p[5]?.trim() === 'DUAL_ALERT',
      kill:  p[6]?.trim() === 'KILL_ON',
      sys:   p[7]?.trim() === 'SYS_ON',
      mU:    parseFloat(p[8]) || 100,
      mS:    parseInt(p[9]) || 50
    };

    await sql`
      INSERT INTO "Upload" (
        "distance", "vibration", "seismic", 
        "dist_alert", "seis_alert", "dual_alert", 
        "kill_state", "sys_state", "min_ultra", "min_seis"
      ) VALUES (
        ${data.dist}, ${data.vib}, ${data.seis}, 
        ${data.dA}, ${data.sA}, ${data.duA}, 
        ${data.kill}, ${data.sys}, ${data.mU}, ${data.mS}
      );
    `;

    return Response.json({ success: true }, { status: 200 });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}
