// /api/volcano.js — Volcano Monitor API v5.1
const { Pool } = require('pg');

// ================================================================
// DATABASE CONNECTION
// ================================================================
const pool = new Pool({
  connectionString: process.env.POSTGRES_URL || process.env.DATABASE_URL || process.env.PGURL,
  ssl: { rejectUnauthorized: false },
  connectionTimeoutMillis: 10000,
  idleTimeoutMillis: 30000,
  max: 10
});

pool.on('connect', () => console.log('[DB] Connected'));
pool.on('error', (err) => console.error('[DB] Pool error:', err.message));

// ================================================================
// TABLE SETUP
// ================================================================
async function ensureTables() {
  const client = await pool.connect();
  try {
    // Original sensor data table
    await client.query(`
      CREATE TABLE IF NOT EXISTS volcano_data (
        id         SERIAL PRIMARY KEY,
        distance   DECIMAL(10,2),
        vibration  INTEGER,
        dist_alert BOOLEAN DEFAULT false,
        vib_alert  BOOLEAN DEFAULT false,
        dual_alert BOOLEAN DEFAULT false,
        kill_state BOOLEAN DEFAULT false,
        sys_state  BOOLEAN DEFAULT false,
        min_ultra  INTEGER DEFAULT 100,
        min_vib    INTEGER DEFAULT 50,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Original commands table
    await client.query(`
      CREATE TABLE IF NOT EXISTS volcano_commands (
        id         SERIAL PRIMARY KEY,
        command    TEXT NOT NULL,
        executed   BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Settings table — stores api_key, like_count, visit_count
    await client.query(`
      CREATE TABLE IF NOT EXISTS volcano_settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
      )
    `);

    // Seed default settings rows if missing
    await client.query(`
      INSERT INTO volcano_settings (key, value)
      VALUES ('api_key', ''), ('like_count', '0'), ('visit_count', '0')
      ON CONFLICT (key) DO NOTHING
    `);

    // Feedback table
    await client.query(`
      CREATE TABLE IF NOT EXISTS volcano_feedback (
        id       BIGINT PRIMARY KEY,
        name     TEXT,
        rating   INTEGER,
        category TEXT,
        message  TEXT,
        device   TEXT,
        ts       TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    console.log('[DB] Tables ensured');
  } catch (err) {
    console.error('[DB] Table setup error:', err.message);
  } finally {
    client.release();
  }
}

ensureTables().catch(err => console.error('[INIT] Failed:', err));

// ================================================================
// HELPERS
// ================================================================
async function getSetting(client, key) {
  const { rows } = await client.query(
    'SELECT value FROM volcano_settings WHERE key = $1',
    [key]
  );
  return rows[0]?.value ?? null;
}

async function setSetting(client, key, value) {
  await client.query(
    `INSERT INTO volcano_settings (key, value) VALUES ($1, $2)
     ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value`,
    [key, String(value)]
  );
}

// ================================================================
// MAIN HANDLER
// ================================================================
module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') return res.status(200).end();

  let client;
  try {
    client = await pool.connect();

    // ==========================================================
    // GET — sensor data + settings + feedback + likes
    // ==========================================================
    if (req.method === 'GET') {
      const action = req.query?.action;

      // Feedback-only fetch
      if (action === 'feedback') {
        const { rows: feedbackRows } = await client.query(
          'SELECT * FROM volcano_feedback ORDER BY created_at DESC LIMIT 200'
        );
        const likeCount = await getSetting(client, 'like_count');
        return res.status(200).json({
          feedback:   feedbackRows,
          like_count: parseInt(likeCount) || 0,
          status: 'ok'
        });
      }

      // Main sensor data fetch
      const { rows: dataRows } = await client.query(`
        SELECT distance, vibration,
               dist_alert, vib_alert, dual_alert,
               kill_state, sys_state,
               min_ultra, min_vib,
               created_at
        FROM volcano_data
        ORDER BY created_at DESC
        LIMIT 1
      `);

      const { rows: cmdRows } = await client.query(`
        SELECT id, command
        FROM volcano_commands
        WHERE executed = false
        ORDER BY created_at ASC
      `);

      // Fetch settings
      const apiKey    = await getSetting(client, 'api_key');
      const likeCount = await getSetting(client, 'like_count');

      // Increment visit count
      const visits = parseInt(await getSetting(client, 'visit_count') || '0') + 1;
      await setSetting(client, 'visit_count', visits);

      const data = dataRows[0] || {
        distance: 0, vibration: 0,
        dist_alert: false, vib_alert: false, dual_alert: false,
        kill_state: false, sys_state: false,
        min_ultra: 100, min_vib: 50
      };

      return res.status(200).json({
        data: {
          ...data,
          api_key:     apiKey || '',
          like_count:  parseInt(likeCount) || 0,
          visit_count: visits,
        },
        commands:  cmdRows,
        status:    'ok',
        timestamp: new Date().toISOString()
      });
    }

    // ==========================================================
    // POST — commands / sensor data / likes / feedback / settings
    // ==========================================================
    if (req.method === 'POST') {
      const body = req.body || {};

      // ── Mark command executed ──
      if (body.executed_id) {
        await client.query(
          'UPDATE volcano_commands SET executed = true WHERE id = $1',
          [body.executed_id]
        );
        return res.status(200).json({ ok: true, action: 'marked_executed' });
      }

      // ── Like / Unlike ──
      if (body.command === 'like_add') {
        const cur = parseInt(await getSetting(client, 'like_count') || '0');
        await setSetting(client, 'like_count', cur + 1);
        return res.status(200).json({ ok: true, action: 'like_added', like_count: cur + 1 });
      }

      if (body.command === 'like_remove') {
        const cur = parseInt(await getSetting(client, 'like_count') || '0');
        await setSetting(client, 'like_count', Math.max(0, cur - 1));
        return res.status(200).json({ ok: true, action: 'like_removed', like_count: Math.max(0, cur - 1) });
      }

      // ── Save API key (cross-device sync) ──
      if (body.command === 'set_api_key') {
        const key = (body.api_key || '').trim();
        await setSetting(client, 'api_key', key);
        return res.status(200).json({ ok: true, action: 'api_key_saved' });
      }

      // ── Submit feedback ──
      if (body.command === 'feedback_add' && body.feedback) {
        const f = body.feedback;
        await client.query(`
          INSERT INTO volcano_feedback (id, name, rating, category, message, device, ts)
          VALUES ($1, $2, $3, $4, $5, $6, $7)
          ON CONFLICT (id) DO NOTHING
        `, [
          f.id       || Date.now(),
          (f.name    || 'ANONYMOUS').slice(0, 40),
          parseInt(f.rating)   || 0,
          (f.category || 'general').slice(0, 20),
          (f.message || '').slice(0, 500),
          (f.device  || 'UNKNOWN').slice(0, 20),
          f.ts       || new Date().toISOString()
        ]);
        return res.status(200).json({ ok: true, action: 'feedback_saved' });
      }

      // ── Queue sensor command ──
      if (body.command) {
        const { rows } = await client.query(
          'INSERT INTO volcano_commands (command) VALUES ($1) RETURNING id',
          [body.command]
        );
        return res.status(200).json({ ok: true, id: rows[0].id, action: 'command_queued' });
      }

      // ── Insert sensor data (from hardware) ──
      const {
        distance, vibration,
        dist_alert = false, vib_alert = false, dual_alert = false,
        kill_state = false, sys_state = false,
        min_ultra = 100, min_vib = 50
      } = body;

      if (distance == null || vibration == null) {
        return res.status(400).json({ error: 'distance and vibration required', received: body });
      }

      await client.query(`
        INSERT INTO volcano_data
          (distance, vibration, dist_alert, vib_alert, dual_alert, kill_state, sys_state, min_ultra, min_vib)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      `, [distance, vibration, dist_alert, vib_alert, dual_alert, kill_state, sys_state, min_ultra, min_vib]);

      // Cleanup sensor data older than 1 hour
      await client.query(`DELETE FROM volcano_data WHERE created_at < NOW() - INTERVAL '1 hour'`);

      return res.status(200).json({ ok: true, action: 'data_inserted', timestamp: new Date().toISOString() });
    }

    return res.status(405).json({ error: 'Method not allowed' });

  } catch (err) {
    console.error('[API ERROR]', err);
    return res.status(500).json({
      error: err.message,
      type:  err.name,
      hint:  'Check POSTGRES_URL or DATABASE_URL env var'
    });
  } finally {
    if (client) client.release();
  }
};
