import { Hono } from 'hono';
import { supabase } from '../lib/supabase';

export const progressRouter = new Hono();

progressRouter.get('/user/:userId', async (c) => {
  const { data, error } = await supabase
    .from('user_concept_progress')
    .select('*, concept:concepts(*)')
    .eq('user_id', c.req.param('userId'));
  if (error) return c.json({ error: error.message }, 500);
  return c.json(data);
});
