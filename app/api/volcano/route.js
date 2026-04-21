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

import { sql } from '@vercel/postgres';

export async function POST(request) {
  try {
    // 1. Get the raw text from your EXE
    const rawData = await request.text(); 
    
    // 2. Split the string by commas
    // Example: "45.67,5,512,DIST_OK,SEIS_ALERT,DUAL_OK,KILL_OFF,SYS_ON,10.0,3"
    const parts = rawData.split(',');

    // 3. Map the parts to variables
    const data = {
      distance:      parseFloat(parts[0]),
      vibration:     parseInt(parts[1]),
      seismic:       parseInt(parts[2]),
      dist_alert:    parts[3] === 'DIST_ALERT',
      seis_alert:    parts[4] === 'SEIS_ALERT',
      dual_alert:    parts[5] === 'DUAL_ALERT',
      kill_state:    parts[6] === 'KILL_ON',
      sys_state:     parts[7] === 'SYS_ON',
      min_ultra:     parseFloat(parts[8]),
      min_seis:      parseInt(parts[9])
    };

    // 4. Push to Vercel Postgres
    await sql`
      INSERT INTO "Upload" (
        "userName", 
        "message", 
        "data"
      ) VALUES (
        'WINDOWS_EXE', 
        'Sensor Update', 
        ${JSON.stringify(data)}
      );
    `;

    return Response.json({ success: true }, { status: 200 });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}

// Keep your GET function as it was to support the APK/Webpage Pulling
