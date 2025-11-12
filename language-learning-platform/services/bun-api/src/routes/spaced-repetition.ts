/**
 * Spaced Repetition API routes
 */
import { Hono } from 'hono';
import { supabase } from '../lib/supabase';

export const spacedRepetitionRouter = new Hono();

// Get cards due for review
spacedRepetitionRouter.get('/due/:userId', async (c) => {
  const userId = c.req.param('userId');
  const limit = parseInt(c.req.query('limit') || '20');

  const { data, error } = await supabase
    .from('spaced_repetition_cards')
    .select(`
      *,
      flashcard:flashcards (*),
      word:words (*),
      concept:concepts (*)
    `)
    .eq('user_id', userId)
    .lte('due_date', new Date().toISOString())
    .order('due_date', { ascending: true })
    .limit(limit);

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  return c.json(data);
});

// Submit a card review
spacedRepetitionRouter.post('/review', async (c) => {
  const body = await c.req.json();

  // Log the review
  const { data: logData, error: logError } = await supabase
    .from('review_logs')
    .insert({
      user_id: body.user_id,
      srs_card_id: body.card_id,
      rating: body.rating, // 1-4
      time_taken_seconds: body.time_taken_seconds,
      previous_ease_factor: body.previous_ease_factor,
      new_ease_factor: body.new_ease_factor,
      previous_interval_days: body.previous_interval_days,
      new_interval_days: body.new_interval_days,
    })
    .select();

  if (logError) {
    return c.json({ error: logError.message }, 500);
  }

  // Update the SRS card
  const { data: cardData, error: cardError } = await supabase
    .from('spaced_repetition_cards')
    .update({
      ease_factor: body.new_ease_factor,
      interval_days: body.new_interval_days,
      repetitions: body.new_repetitions,
      lapses: body.new_lapses,
      card_state: body.new_state,
      due_date: body.new_due_date,
      last_reviewed_at: new Date().toISOString(),
    })
    .eq('id', body.card_id)
    .select()
    .single();

  if (cardError) {
    return c.json({ error: cardError.message }, 500);
  }

  return c.json({
    log: logData,
    card: cardData,
  });
});

// Get review statistics
spacedRepetitionRouter.get('/stats/:userId', async (c) => {
  const userId = c.req.param('userId');

  // Get review counts by state
  const { data, error } = await supabase
    .from('spaced_repetition_cards')
    .select('card_state')
    .eq('user_id', userId);

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  const stats = {
    new: 0,
    learning: 0,
    review: 0,
    relearning: 0,
    total: data.length,
  };

  data.forEach((card: any) => {
    stats[card.card_state as keyof typeof stats]++;
  });

  // Get reviews today
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const { count } = await supabase
    .from('review_logs')
    .select('*', { count: 'exact', head: true })
    .eq('user_id', userId)
    .gte('reviewed_at', today.toISOString());

  return c.json({
    ...stats,
    reviews_today: count || 0,
  });
});
