/**
 * Bun TypeScript API for Language Learning Platform
 *
 * Fast API service using Bun and Hono for:
 * - Language and concept management
 * - User progress tracking
 * - Flashcard and quiz retrieval
 * - Learning plan management
 */
import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { prettyJSON } from 'hono/pretty-json';

import { languagesRouter } from './routes/languages';
import { conceptsRouter } from './routes/concepts';
import { flashcardsRouter } from './routes/flashcards';
import { quizzesRouter } from './routes/quizzes';
import { storiesRouter } from './routes/stories';
import { progressRouter } from './routes/progress';
import { learningPlansRouter } from './routes/learning-plans';
import { spacedRepetitionRouter } from './routes/spaced-repetition';

const app = new Hono();

// Middleware
app.use('*', logger());
app.use('*', prettyJSON());
app.use('*', cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true,
}));

// Health check
app.get('/', (c) => {
  return c.json({
    service: 'language-learning-bun-api',
    status: 'healthy',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
  });
});

app.get('/health', (c) => {
  return c.json({ status: 'ok' });
});

// API Routes
app.route('/api/v1/languages', languagesRouter);
app.route('/api/v1/concepts', conceptsRouter);
app.route('/api/v1/flashcards', flashcardsRouter);
app.route('/api/v1/quizzes', quizzesRouter);
app.route('/api/v1/stories', storiesRouter);
app.route('/api/v1/progress', progressRouter);
app.route('/api/v1/learning-plans', learningPlansRouter);
app.route('/api/v1/spaced-repetition', spacedRepetitionRouter);

// 404 handler
app.notFound((c) => {
  return c.json({ error: 'Not found' }, 404);
});

// Error handler
app.onError((err, c) => {
  console.error('Error:', err);
  return c.json({ error: err.message || 'Internal server error' }, 500);
});

const port = parseInt(process.env.PORT || '3001');

console.log(`🚀 Bun API server starting on port ${port}`);

export default {
  port,
  fetch: app.fetch,
};
