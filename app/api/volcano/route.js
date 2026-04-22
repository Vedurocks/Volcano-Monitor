import { Pool } from 'pg';

// Using your Prisma connection string
const connectionString = "postgres://4d25951a202fb0d6375a443e4d190433c772440e3eb8d832c99a06f3824dfa76:sk_qUug2x2t-TL6c5GRBBt47@db.prisma.io:5432/postgres?sslmode=require";

const pool = new Pool({
  connectionString,
});

export async function GET() {
  try {
    const { rows } = await pool.query('SELECT * FROM "Upload" ORDER BY "createdAt" DESC LIMIT 50');
    return Response.json(rows, {
      status: 200,
      headers: { 'Access-Control-Allow-Origin': '*' }
    });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const raw = await request.text();
    
    // Handle Startup Message
    if (raw.includes("MIN_ULTRA")) {
      return Response.json({ success: "System Startup Logged" }, { status: 200 });
    }

    // Process Data Line: 45.67,0,DIST_OK,VIB_OK,DUAL_OK,KILL_OFF,SYS_ON,10.0,3
    const p = raw.split(',');
    if (p.length < 9) throw new Error("Format Mismatch");

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

    const query = `
      INSERT INTO "Upload" (
        "distance", "vibration", "dist_alert", "seis_alert", 
        "dual_alert", "kill_state", "sys_state", "min_ultra", "min_seis"
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    `;
    
    const values = [
      data.dist, data.vib, data.dA, data.vA, 
      data.duA, data.kill, data.sys, data.mU, data.mV
    ];

    await pool.query(query, values);

    return Response.json({ success: true }, { 
        status: 200,
        headers: { 'Access-Control-Allow-Origin': '*' }
    });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}
