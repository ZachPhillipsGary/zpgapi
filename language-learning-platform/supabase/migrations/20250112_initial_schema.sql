-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Languages table
CREATE TABLE languages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) NOT NULL UNIQUE, -- ISO 639-1 (e.g., 'en', 'fr', 'zh-TW')
    native_name VARCHAR(100) NOT NULL, -- e.g., 'Français', '中文'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User languages (many-to-many with auth.users from Supabase)
CREATE TABLE user_languages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    proficiency_level VARCHAR(20) DEFAULT 'beginner', -- beginner, intermediate, advanced, native
    daily_goal_minutes INTEGER DEFAULT 15,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_practiced_at TIMESTAMPTZ,
    total_study_time_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, language_id)
);

-- Concepts (phrases, grammar points, vocabulary themes)
CREATE TABLE concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    language_id UUID NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    concept_type VARCHAR(50) NOT NULL, -- phrase, grammar, vocabulary, idiom
    difficulty_level INTEGER DEFAULT 1, -- 1-10 scale
    category VARCHAR(100), -- e.g., 'greetings', 'past_tense', 'business'
    prerequisites JSONB DEFAULT '[]'::jsonb, -- Array of concept IDs
    metadata JSONB DEFAULT '{}'::jsonb,
    is_published BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_concepts_language ON concepts(language_id);
CREATE INDEX idx_concepts_type ON concepts(concept_type);
CREATE INDEX idx_concepts_difficulty ON concepts(difficulty_level);

-- Words within concepts
CREATE TABLE words (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    word TEXT NOT NULL,
    translation TEXT NOT NULL,
    pronunciation TEXT, -- IPA or pinyin
    romanization TEXT, -- For languages like Mandarin
    part_of_speech VARCHAR(50), -- noun, verb, adjective, etc.
    example_sentence TEXT,
    example_translation TEXT,
    audio_url TEXT,
    image_url TEXT,
    frequency_rank INTEGER, -- How common the word is
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_words_concept ON words(concept_id);

-- User concept progress
CREATE TABLE user_concept_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    mastery_level DECIMAL(3, 2) DEFAULT 0.0, -- 0.0 to 1.0
    review_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    last_reviewed_at TIMESTAMPTZ,
    next_review_date TIMESTAMPTZ,
    is_learning BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, concept_id)
);

CREATE INDEX idx_user_concept_progress_user ON user_concept_progress(user_id);
CREATE INDEX idx_user_concept_progress_next_review ON user_concept_progress(next_review_date);

-- Flashcards
CREATE TABLE flashcards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    card_type VARCHAR(50) DEFAULT 'basic', -- basic, cloze, audio, image
    hint TEXT,
    audio_front_url TEXT,
    audio_back_url TEXT,
    image_url TEXT,
    is_ai_generated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_flashcards_concept ON flashcards(concept_id);

-- Stories
CREATE TABLE stories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    difficulty INTEGER DEFAULT 1, -- 1-10 scale
    estimated_reading_time INTEGER, -- in minutes
    audio_url TEXT,
    cover_image_url TEXT,
    vocabulary JSONB DEFAULT '[]'::jsonb, -- Array of key words
    is_ai_generated BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stories_concept ON stories(concept_id);
CREATE INDEX idx_stories_difficulty ON stories(difficulty);

-- Quizzes
CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    questions JSONB NOT NULL, -- Array of question objects
    passing_score INTEGER DEFAULT 70,
    time_limit_minutes INTEGER,
    is_ai_generated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_quizzes_concept ON quizzes(concept_id);

-- User quiz attempts
CREATE TABLE quiz_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    answers JSONB NOT NULL,
    time_taken_seconds INTEGER,
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_quiz_attempts_user ON quiz_attempts(user_id);
CREATE INDEX idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);

-- Spaced repetition data (Anki algorithm)
CREATE TABLE spaced_repetition_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    flashcard_id UUID REFERENCES flashcards(id) ON DELETE CASCADE,
    word_id UUID REFERENCES words(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,

    -- Anki algorithm fields (SM-2)
    ease_factor DECIMAL(4, 2) DEFAULT 2.50, -- Starting at 2.5
    interval_days INTEGER DEFAULT 1, -- Days until next review
    repetitions INTEGER DEFAULT 0,
    lapses INTEGER DEFAULT 0, -- Number of times forgotten

    -- Review state
    card_state VARCHAR(20) DEFAULT 'new', -- new, learning, review, relearning
    due_date TIMESTAMPTZ NOT NULL,
    last_reviewed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure only one reference type per card
    CONSTRAINT check_single_reference CHECK (
        (flashcard_id IS NOT NULL)::integer +
        (word_id IS NOT NULL)::integer +
        (concept_id IS NOT NULL)::integer = 1
    )
);

CREATE INDEX idx_srs_cards_user ON spaced_repetition_cards(user_id);
CREATE INDEX idx_srs_cards_due ON spaced_repetition_cards(due_date);
CREATE INDEX idx_srs_cards_state ON spaced_repetition_cards(card_state);

-- Review history log
CREATE TABLE review_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    srs_card_id UUID NOT NULL REFERENCES spaced_repetition_cards(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL, -- 1 (again), 2 (hard), 3 (good), 4 (easy)
    time_taken_seconds INTEGER,
    previous_ease_factor DECIMAL(4, 2),
    new_ease_factor DECIMAL(4, 2),
    previous_interval_days INTEGER,
    new_interval_days INTEGER,
    reviewed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_review_logs_user ON review_logs(user_id);
CREATE INDEX idx_review_logs_card ON review_logs(srs_card_id);

-- Tutoring sessions (Pipecat sessions)
CREATE TABLE tutoring_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE SET NULL,
    session_type VARCHAR(50) DEFAULT 'conversation', -- conversation, pronunciation, grammar_practice
    duration_seconds INTEGER,
    transcript JSONB, -- Array of conversation turns
    feedback JSONB, -- AI-generated feedback
    recording_url TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_tutoring_sessions_user ON tutoring_sessions(user_id);
CREATE INDEX idx_tutoring_sessions_language ON tutoring_sessions(language_id);

-- AI content generation queue
CREATE TABLE ai_generation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL, -- story, quiz, flashcards, video
    language_id UUID NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    priority INTEGER DEFAULT 5, -- 1-10, higher = more important
    parameters JSONB DEFAULT '{}'::jsonb,
    result_id UUID, -- References the created content
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_ai_jobs_status ON ai_generation_jobs(status);
CREATE INDEX idx_ai_jobs_priority ON ai_generation_jobs(priority DESC);

-- User settings and preferences
CREATE TABLE user_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    native_language_id UUID REFERENCES languages(id),
    theme VARCHAR(20) DEFAULT 'light', -- light, dark, auto
    notifications_enabled BOOLEAN DEFAULT true,
    daily_reminder_time TIME,
    audio_autoplay BOOLEAN DEFAULT true,
    study_streak_days INTEGER DEFAULT 0,
    last_study_date DATE,
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed initial languages
INSERT INTO languages (code, name, native_name) VALUES
    ('en', 'English', 'English'),
    ('fr', 'French', 'Français'),
    ('zh-TW', 'Mandarin (Traditional)', '中文（繁體）');

-- Row Level Security (RLS) Policies
ALTER TABLE user_languages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_concept_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE spaced_repetition_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE review_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tutoring_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY user_languages_policy ON user_languages FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_concept_progress_policy ON user_concept_progress FOR ALL USING (auth.uid() = user_id);
CREATE POLICY srs_cards_policy ON spaced_repetition_cards FOR ALL USING (auth.uid() = user_id);
CREATE POLICY review_logs_policy ON review_logs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY quiz_attempts_policy ON quiz_attempts FOR ALL USING (auth.uid() = user_id);
CREATE POLICY tutoring_sessions_policy ON tutoring_sessions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY user_preferences_policy ON user_preferences FOR ALL USING (auth.uid() = user_id);

-- Public read access for content (languages, concepts, words, flashcards, stories, quizzes)
ALTER TABLE languages ENABLE ROW LEVEL SECURITY;
ALTER TABLE concepts ENABLE ROW LEVEL SECURITY;
ALTER TABLE words ENABLE ROW LEVEL SECURITY;
ALTER TABLE flashcards ENABLE ROW LEVEL SECURITY;
ALTER TABLE stories ENABLE ROW LEVEL SECURITY;
ALTER TABLE quizzes ENABLE ROW LEVEL SECURITY;

CREATE POLICY languages_select_policy ON languages FOR SELECT USING (is_active = true);
CREATE POLICY concepts_select_policy ON concepts FOR SELECT USING (is_published = true);
CREATE POLICY words_select_policy ON words FOR SELECT USING (true);
CREATE POLICY flashcards_select_policy ON flashcards FOR SELECT USING (true);
CREATE POLICY stories_select_policy ON stories FOR SELECT USING (true);
CREATE POLICY quizzes_select_policy ON quizzes FOR SELECT USING (true);

-- Functions for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for all tables with updated_at
CREATE TRIGGER update_languages_updated_at BEFORE UPDATE ON languages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_languages_updated_at BEFORE UPDATE ON user_languages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_concepts_updated_at BEFORE UPDATE ON concepts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_words_updated_at BEFORE UPDATE ON words FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_concept_progress_updated_at BEFORE UPDATE ON user_concept_progress FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_flashcards_updated_at BEFORE UPDATE ON flashcards FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_stories_updated_at BEFORE UPDATE ON stories FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_srs_cards_updated_at BEFORE UPDATE ON spaced_repetition_cards FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
