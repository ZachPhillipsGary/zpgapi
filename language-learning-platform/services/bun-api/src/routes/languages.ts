/**
 * Languages API routes
 */
import { Hono } from 'hono';
import { supabase } from '../lib/supabase';

export const languagesRouter = new Hono();

// Get all active languages
languagesRouter.get('/', async (c) => {
  const { data, error } = await supabase
    .from('languages')
    .select('*')
    .eq('is_active', true)
    .order('name');

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  return c.json(data);
});

// Get language by ID
languagesRouter.get('/:id', async (c) => {
  const id = c.req.param('id');

  const { data, error } = await supabase
    .from('languages')
    .select('*')
    .eq('id', id)
    .single();

  if (error) {
    return c.json({ error: error.message }, error.code === 'PGRST116' ? 404 : 500);
  }

  return c.json(data);
});

// Get user's enrolled languages
languagesRouter.get('/user/:userId', async (c) => {
  const userId = c.req.param('userId');

  const { data, error } = await supabase
    .from('user_languages')
    .select(`
      *,
      language:languages (*)
    `)
    .eq('user_id', userId)
    .order('started_at', { ascending: false });

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  return c.json(data);
});

// Enroll user in a language
languagesRouter.post('/user/:userId/enroll', async (c) => {
  const userId = c.req.param('userId');
  const body = await c.req.json();

  const { data, error } = await supabase
    .from('user_languages')
    .insert({
      user_id: userId,
      language_id: body.language_id,
      proficiency_level: body.proficiency_level || 'beginner',
      daily_goal_minutes: body.daily_goal_minutes || 15,
    })
    .select()
    .single();

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  return c.json(data, 201);
});
