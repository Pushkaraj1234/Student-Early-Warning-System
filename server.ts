import express from 'express';
import path from 'path';
import dotenv from 'dotenv';
import { createServer as createViteServer } from 'vite';
import { getDb } from './server/db.js';
import { initializeSchema } from './server/schema.js';
import { seedDatabaseIfEmpty } from './server/seedData.js';
import { apiRouter } from './server/routes.js';

dotenv.config();

const PORT = 3000;
const HOST = '0.0.0.0';

async function startServer() {
  const app = express();

  // Basic middleware
  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true, limit: '10mb' }));

  // Initialize Relational Database & Seed Data
  try {
    const db = await getDb();
    initializeSchema(db);
    await seedDatabaseIfEmpty(db);
    console.log('[SEWS] Relational SQLite database initialized & verified.');
  } catch (err) {
    console.error('[SEWS] Database initialization error:', err);
  }

  // Health check endpoint
  app.get('/api/health', (req, res) => {
    res.json({
      status: 'ok',
      service: 'Student Early Warning System (SEWS)',
      timestamp: new Date().toISOString()
    });
  });

  // REST API Routes FIRST
  app.use('/api', apiRouter);

  // Vite middleware for development or Static files in production
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, HOST, () => {
    console.log(`[SEWS] Server listening at http://${HOST}:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('[SEWS] Fatal startup failure:', err);
});
