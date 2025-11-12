import { Hono } from 'hono';
import { supabase } from '../lib/supabase';

export const flashcardsRouter = new Hono();

flashcardsRouter.get('/concept/:conceptId', async (c) => {
  const { data, error } = await supabase
    .from('flashcards')
    .select('*')
    .eq('concept_id', c.req.param('conceptId'));
  if (error) return c.json({ error: error.message }, 500);
  return c.json(data);
});
