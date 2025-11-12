/**
 * Learning Plans API routes
 */
import { Hono } from 'hono';
import { supabase, supabaseAdmin } from '../lib/supabase';

export const learningPlansRouter = new Hono();

// Get all public learning plans for a language
learningPlansRouter.get('/language/:languageId', async (c) => {
  const languageId = c.req.param('languageId');
  const featured = c.req.query('featured');

  let query = supabase
    .from('learning_plans')
    .select(`
      *,
      language:languages (*),
      concept_count:learning_plan_concepts(count)
    `)
    .eq('language_id', languageId)
    .eq('is_public', true)
    .eq('is_published', true);

  if (featured === 'true') {
    query = query.eq('is_featured', true);
  }

  const { data, error } = await query.order('enrollment_count', { ascending: false });

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  return c.json(data);
});

// Get learning plan details with concepts
learningPlansRouter.get('/:id', async (c) => {
  const id = c.req.param('id');

  const { data, error } = await supabase
    .from('learning_plans')
    .select(`
      *,
      language:languages (*),
      concepts:learning_plan_concepts (
        *,
        concept:concepts (*)
      )
    `)
    .eq('id', id)
    .single();

  if (error) {
    return c.json({ error: error.message }, 404);
  }

  // Sort concepts by sequence_order
  if (data.concepts) {
    data.concepts.sort((a: any, b: any) => a.sequence_order - b.sequence_order);
  }

  return c.json(data);
});

// Enroll user in a learning plan
learningPlansRouter.post('/:id/enroll', async (c) => {
  const planId = c.req.param('id');
  const body = await c.req.json();
  const userId = body.user_id;

  // Get total concept count
  const { count } = await supabase
    .from('learning_plan_concepts')
    .select('*', { count: 'exact', head: true })
    .eq('learning_plan_id', planId);

  const { data, error } = await supabase
    .from('user_learning_plans')
    .insert({
      user_id: userId,
      learning_plan_id: planId,
      total_concept_count: count || 0,
    })
    .select()
    .single();

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  return c.json(data, 201);
});

// Get user's enrolled plans
learningPlansRouter.get('/user/:userId/enrolled', async (c) => {
  const userId = c.req.param('userId');

  const { data, error } = await supabase
    .from('user_learning_plans')
    .select(`
      *,
      learning_plan:learning_plans (
        *,
        language:languages (*)
      )
    `)
    .eq('user_id', userId)
    .order('started_at', { ascending: false });

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  return c.json(data);
});

// Update user progress in a plan
learningPlansRouter.patch('/:planId/progress', async (c) => {
  const planId = c.req.param('planId');
  const body = await c.req.json();

  const { data, error } = await supabase
    .from('user_plan_concept_progress')
    .upsert({
      user_learning_plan_id: body.user_learning_plan_id,
      concept_id: body.concept_id,
      is_completed: body.is_completed,
      completion_percentage: body.completion_percentage,
      stories_read: body.stories_read || 0,
      quizzes_passed: body.quizzes_passed || 0,
      flashcards_reviewed: body.flashcards_reviewed || 0,
      tutoring_sessions: body.tutoring_sessions || 0,
    })
    .select()
    .single();

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  return c.json(data);
});

// Create a new learning plan (admin only)
learningPlansRouter.post('/', async (c) => {
  const body = await c.req.json();

  const { data, error } = await supabaseAdmin
    .from('learning_plans')
    .insert({
      language_id: body.language_id,
      title: body.title,
      description: body.description,
      difficulty_level: body.difficulty_level || 1,
      estimated_hours: body.estimated_hours,
      category: body.category,
      tags: body.tags || [],
      created_by: body.created_by,
      is_public: body.is_public !== false,
      is_published: body.is_published || false,
    })
    .select()
    .single();

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  return c.json(data, 201);
});

// Add concepts to a learning plan
learningPlansRouter.post('/:id/concepts', async (c) => {
  const planId = c.req.param('id');
  const body = await c.req.json();

  // body.concepts should be an array of { concept_id, sequence_order, is_required?, notes? }
  const conceptsToAdd = body.concepts.map((concept: any) => ({
    learning_plan_id: planId,
    concept_id: concept.concept_id,
    sequence_order: concept.sequence_order,
    is_required: concept.is_required !== false,
    notes: concept.notes,
  }));

  const { data, error } = await supabaseAdmin
    .from('learning_plan_concepts')
    .insert(conceptsToAdd)
    .select();

  if (error) {
    return c.json({ error: error.message }, 500);
  }

  return c.json(data, 201);
});
