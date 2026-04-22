// /api/volcano.js — Volcano Monitor API v5.0 (Fixed)
const { Pool } = require('pg');

// ================================================================
// DATABASE CONNECTION — Fixed: Explicit connection string with SSL
// ================================================================
const pool = new Pool({
  connectionString: process.env.POSTGRES_URL || process.env.DATABASE_URL || process.env.PGURL,
  ssl: { rejectUnauthorized: false }, // Required for Neon/Vercel Postgres
  connectionTimeoutMillis: 10000,
  idleTimeoutMillis: 30000,
  max: 10
});

// Log connection status on startup
pool.on('connect', () => console.log('[DB] Connected'));
pool.on('error', (err) => console.error('[DB] Pool error:', err.message));

// ================================================================
// TABLE SETUP — Auto-create tables if they don't exist
// ================================================================
async function ensureTables() {
  const client = await pool.connect();
  try {
    await client.query(`
      CREATE TABLE IF NOT EXISTS volcano_data (
        id SERIAL PRIMARY KEY,
        distance DECIMAL(10,2),
        vibration INTEGER,
        dist_alert BOOLEAN DEFAULT false,
        vib_alert BOOLEAN DEFAULT false,
        dual_alert BOOLEAN DEFAULT false,
        kill_state BOOLEAN DEFAULT false,
        sys_state BOOLEAN DEFAULT false,
        min_ultra INTEGER DEFAULT 100,
        min_vib INTEGER DEFAULT 50,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    await client.query(`
      CREATE TABLE IF NOT EXISTS volcano_commands (
        id SERIAL PRIMARY KEY,
        command TEXT NOT NULL,
        executed BOOLEAN DEFAULT false,
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

// Run table setup immediately
ensureTables().catch(err => console.error('[INIT] Failed:', err));

// ================================================================
// MAIN HANDLER
// ================================================================
module.exports = async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') return res.status(200).end();

  let client;
  try {
    // Get client from pool
    client = await pool.connect();
    
    // ============================================================
    // GET — Fetch latest data + pending commands
    // ============================================================
    if (req.method === 'GET') {
      const { rows: dataRows } = await client.query(`
        SELECT 
          distance, vibration,
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
      
      const data = dataRows[0] || {
        distance: 0, vibration: 0,
        dist_alert: false, vib_alert: false, dual_alert: false,
        kill_state: false, sys_state: false,
        min_ultra: 100, min_vib: 50
      };
      
      return res.status(200).json({ 
        data, 
        commands: cmdRows,
        status: 'ok',
        timestamp: new Date().toISOString()
      });
    }

    // ============================================================
    // POST — Insert data or queue commands
    // ============================================================
    if (req.method === 'POST') {
      const body = req.body || {};

      // Mark command as executed
      if (body.executed_id) {
        await client.query(
          'UPDATE volcano_commands SET executed = true WHERE id = $1',
          [body.executed_id]
        );
        return res.status(200).json({ ok: true, action: 'marked_executed' });
      }

      // Queue new command
      if (body.command) {
        const { rows } = await client.query(
          'INSERT INTO volcano_commands (command) VALUES ($1) RETURNING id',
          [body.command]
        );
        return res.status(200).json({ 
          ok: true, 
          id: rows[0].id,
          action: 'command_queued'
        });
      }

      // Insert sensor data
      const {
        distance, vibration,
        dist_alert = false, vib_alert = false, dual_alert = false,
        kill_state = false, sys_state = false,
        min_ultra = 100, min_vib = 50
      } = body;

      if (distance == null || vibration == null) {
        return res.status(400).json({ 
          error: 'distance and vibration required',
          received: body 
        });
      }

      await client.query(`
        INSERT INTO volcano_data
          (distance, vibration, dist_alert, vib_alert, dual_alert, kill_state, sys_state, min_ultra, min_vib)
        VALUES
          ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      `, [
        distance, vibration,
        dist_alert, vib_alert, dual_alert,
        kill_state, sys_state,
        min_ultra, min_vib
      ]);

      // Cleanup old data (> 1 hour)
      await client.query(`
        DELETE FROM volcano_data 
        WHERE created_at < NOW() - INTERVAL '1 hour'
      `);

      return res.status(200).json({ 
        ok: true, 
        action: 'data_inserted',
        timestamp: new Date().toISOString()
      });
    }

    return res.status(405).json({ error: 'Method not allowed' });

  } catch (err) {
    console.error('[API ERROR]', err);
    return res.status(500).json({ 
      error: err.message,
      type: err.name,
      hint: 'Check POSTGRES_URL or DATABASE_URL env var'
    });
  } finally {
    if (client) client.release();
  }
};
