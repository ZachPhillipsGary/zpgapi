import { Hono } from 'hono';
import { supabase } from '../lib/supabase';

export const conceptsRouter = new Hono();

conceptsRouter.get('/', async (c) => {
  const languageId = c.req.query('language_id');
  const { data, error } = await supabase
    .from('concepts')
    .select('*')
    .eq('language_id', languageId)
    .eq('is_published', true)
    .order('difficulty_level');
  if (error) return c.json({ error: error.message }, 500);
  return c.json(data);
});

conceptsRouter.get('/:id', async (c) => {
  const { data, error } = await supabase
    .from('concepts')
    .select('*, words(*)')
    .eq('id', c.req.param('id'))
    .single();
  if (error) return c.json({ error: error.message }, 404);
  return c.json(data);
});
