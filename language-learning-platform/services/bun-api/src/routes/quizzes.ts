import { Hono } from 'hono';
import { supabase } from '../lib/supabase';

export const quizzesRouter = new Hono();

quizzesRouter.get('/concept/:conceptId', async (c) => {
  const { data, error } = await supabase
    .from('quizzes')
    .select('*')
    .eq('concept_id', c.req.param('conceptId'));
  if (error) return c.json({ error: error.message }, 500);
  return c.json(data);
});

quizzesRouter.post('/attempt', async (c) => {
  const body = await c.req.json();
  const { data, error } = await supabase
    .from('quiz_attempts')
    .insert(body)
    .select()
    .single();
  if (error) return c.json({ error: error.message }, 500);
  return c.json(data, 201);
});
