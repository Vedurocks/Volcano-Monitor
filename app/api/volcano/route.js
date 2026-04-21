import { sql } from '@vercel/postgres';

export async function POST(request) {
  try {
    const raw = await request.text();
    
    // 1. Check if it's the Startup Message
    if (raw.includes("MIN_ULTRA")) {
      console.log("System Startup Received:", raw);
      return Response.json({ success: "Startup Logged" }, { status: 200 });
    }

    // 2. Process Data Line
    const p = raw.split(',');
    if (p.length < 9) throw new Error("Incomplete data string");

    const data = {
      dist:  parseFloat(p[0]) || 0,
      vib:   parseInt(p[1]) || 0,
      dA:    p[2]?.trim() === 'DIST_ALERT',
      vA:    p[3]?.trim() === 'VIB_ALERT',
      duA:   p[4]?.trim() === 'DUAL_ALERT',
      kill:  p[5]?.trim() === 'KILL_ON',
      sys:   p[6]?.trim() === 'SYS_ON',
      mU:    parseFloat(p[7]) || 10.0,
      mV:    parseInt(p[8]) || 3
    };

    // 3. Insert into Database
    await sql`
      INSERT INTO "Upload" (
        "distance", "vibration", 
        "dist_alert", "seis_alert", "dual_alert", 
        "kill_state", "sys_state", "min_ultra", "min_seis"
      ) VALUES (
        ${data.dist}, ${data.vib}, 
        ${data.dA}, ${data.vA}, ${data.duA}, 
        ${data.kill}, ${data.sys}, ${data.mU}, ${data.mV}
      );
    `;

    return Response.json({ success: true }, { status: 200 });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}

export async function GET() {
    const { rows } = await sql`SELECT * FROM "Upload" ORDER BY "createdAt" DESC LIMIT 50`;
    return Response.json(rows);
}
