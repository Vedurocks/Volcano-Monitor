import { sql } from '@vercel/postgres';

export default async function handler(req, res) {
  // Allow all origins (so your HTML file can fetch it)
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // ── GET: return latest sensor reading ──────────────────────────
  if (req.method === 'GET') {
    const { rows } = await sql`
      SELECT * FROM volcano_data
      ORDER BY created_at DESC
      LIMIT 1
    `;
    if (rows.length === 0) return res.status(200).json({ message: 'No data yet' });
    return res.status(200).json(rows[0]);
  }

  // ── POST: insert sensor data OR store a command ─────────────────
  if (req.method === 'POST') {
    const body = req.body;

    // If it's a command (from the web shell/AI)
    if (body.command) {
      await sql`
        INSERT INTO volcano_commands (command, executed)
        VALUES (${body.command}, false)
      `;
      return res.status(200).json({ ok: true, command: body.command });
    }

    // If it's sensor data (from Arduino via HTTP)
    const {
      distance, seismic,
      dist_alert, seis_alert, dual_alert,
      kill_state, sys_state,
      min_ultra, min_seis
    } = body;

    await sql`
      INSERT INTO volcano_data
        (distance, seismic, dist_alert, seis_alert, dual_alert,
         kill_state, sys_state, min_ultra, min_seis)
      VALUES
        (${distance}, ${seismic}, ${dist_alert}, ${seis_alert}, ${dual_alert},
         ${kill_state}, ${sys_state}, ${min_ultra}, ${min_seis})
    `;
    return res.status(200).json({ ok: true });
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
