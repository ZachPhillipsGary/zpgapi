import { Hono } from 'hono';
import { supabase } from '../lib/supabase';

export const storiesRouter = new Hono();

storiesRouter.get('/concept/:conceptId', async (c) => {
  const { data, error } = await supabase
    .from('stories')
    .select('*')
    .eq('concept_id', c.req.param('conceptId'));
  if (error) return c.json({ error: error.message }, 500);
  return c.json(data);
});
