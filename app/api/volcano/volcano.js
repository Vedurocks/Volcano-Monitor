import { sql } from '@vercel/postgres';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // ── GET: latest sensor row + any pending commands ──────────────
  if (req.method === 'GET') {
    const { rows: data } = await sql`
      SELECT * FROM volcano_data
      ORDER BY created_at DESC LIMIT 1
    `;
    const { rows: cmds } = await sql`
      SELECT id, command FROM volcano_commands
      WHERE executed = false
      ORDER BY created_at ASC
    `;
    return res.status(200).json({
      data:     data[0] || null,
      commands: cmds          // EXE polls this and executes them
    });
  }

  // ── POST ────────────────────────────────────────────────────────
  if (req.method === 'POST') {
    const body = req.body;

    // --- EXE marks a command as executed after running it
    if (body.executed_id) {
      await sql`
        UPDATE volcano_commands
        SET executed = true
        WHERE id = ${body.executed_id}
      `;
      return res.status(200).json({ ok: true });
    }

    // --- Web / APK sends a command (on, off, kill, etc.)
    if (body.command) {
      const { rows } = await sql`
        INSERT INTO volcano_commands (command)
        VALUES (${body.command})
        RETURNING id
      `;
      return res.status(200).json({ ok: true, id: rows[0].id });
    }

    // --- EXE posts sensor data
    const {
      distance, vibration,
      dist_alert  = false,
      vib_alert   = false,
      dual_alert  = false,
      kill_state  = false,
      sys_state   = false,
      min_ultra   = 100,
      min_vib     = 50
    } = body;

    if (distance == null || vibration == null) {
      return res.status(400).json({ error: 'distance and vibration are required' });
    }

    await sql`
      INSERT INTO volcano_data
        (distance, vibration, dist_alert, vib_alert, dual_alert,
         kill_state, sys_state, min_ultra, min_vib)
      VALUES
        (${distance}, ${vibration},
         ${dist_alert}, ${vib_alert}, ${dual_alert},
         ${kill_state}, ${sys_state}, ${min_ultra}, ${min_vib})
    `;
    return res.status(200).json({ ok: true });
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
    return res.status(200).json({ ok: true });
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
