-- Learning Plans System
-- Allows creating curated groupings of concepts that can be shared among users

-- Learning plans (curated learning paths)
CREATE TABLE learning_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    language_id UUID NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty_level INTEGER DEFAULT 1, -- 1-10 scale
    estimated_hours INTEGER, -- Estimated time to complete
    is_public BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,

    -- Creator info (can be admin or user)
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,

    -- Ordering and categorization
    category VARCHAR(100), -- e.g., 'beginner_course', 'business', 'travel'
    tags JSONB DEFAULT '[]'::jsonb, -- Array of tags for discovery

    -- Media
    cover_image_url TEXT,
    preview_video_url TEXT,

    -- Stats
    enrollment_count INTEGER DEFAULT 0,
    completion_count INTEGER DEFAULT 0,
    average_rating DECIMAL(3, 2) DEFAULT 0.0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    is_published BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_learning_plans_language ON learning_plans(language_id);
CREATE INDEX idx_learning_plans_public ON learning_plans(is_public) WHERE is_public = true;
CREATE INDEX idx_learning_plans_featured ON learning_plans(is_featured) WHERE is_featured = true;
CREATE INDEX idx_learning_plans_category ON learning_plans(category);

-- Many-to-many relationship between learning plans and concepts
CREATE TABLE learning_plan_concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learning_plan_id UUID NOT NULL REFERENCES learning_plans(id) ON DELETE CASCADE,
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,

    -- Ordering within the plan
    sequence_order INTEGER NOT NULL,

    -- Optional: make some concepts optional vs required
    is_required BOOLEAN DEFAULT true,

    -- Optional: add notes or instructions for this concept in this plan
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(learning_plan_id, concept_id),
    UNIQUE(learning_plan_id, sequence_order)
);

CREATE INDEX idx_plan_concepts_plan ON learning_plan_concepts(learning_plan_id);
CREATE INDEX idx_plan_concepts_concept ON learning_plan_concepts(concept_id);
CREATE INDEX idx_plan_concepts_order ON learning_plan_concepts(learning_plan_id, sequence_order);

-- User enrollment in learning plans (many-to-many)
CREATE TABLE user_learning_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    learning_plan_id UUID NOT NULL REFERENCES learning_plans(id) ON DELETE CASCADE,

    -- Progress tracking
    current_concept_index INTEGER DEFAULT 0, -- Index in sequence_order
    completed_concept_count INTEGER DEFAULT 0,
    total_concept_count INTEGER DEFAULT 0, -- Cached for performance

    -- Status
    status VARCHAR(20) DEFAULT 'active', -- active, paused, completed, abandoned
    progress_percentage DECIMAL(5, 2) DEFAULT 0.0,

    -- Engagement
    last_accessed_at TIMESTAMPTZ,
    time_spent_minutes INTEGER DEFAULT 0,

    -- Completion tracking
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- User rating/feedback
    user_rating INTEGER, -- 1-5 stars
    user_review TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, learning_plan_id)
);

CREATE INDEX idx_user_learning_plans_user ON user_learning_plans(user_id);
CREATE INDEX idx_user_learning_plans_plan ON user_learning_plans(learning_plan_id);
CREATE INDEX idx_user_learning_plans_status ON user_learning_plans(status);

-- Track user progress on individual concepts within a plan
CREATE TABLE user_plan_concept_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_learning_plan_id UUID NOT NULL REFERENCES user_learning_plans(id) ON DELETE CASCADE,
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,

    -- Progress tracking
    is_completed BOOLEAN DEFAULT false,
    completion_percentage DECIMAL(5, 2) DEFAULT 0.0,

    -- Activities completed
    stories_read INTEGER DEFAULT 0,
    quizzes_passed INTEGER DEFAULT 0,
    flashcards_reviewed INTEGER DEFAULT 0,
    tutoring_sessions INTEGER DEFAULT 0,

    -- Time tracking
    time_spent_minutes INTEGER DEFAULT 0,
    first_started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_learning_plan_id, concept_id)
);

CREATE INDEX idx_user_plan_progress_user_plan ON user_plan_concept_progress(user_learning_plan_id);
CREATE INDEX idx_user_plan_progress_concept ON user_plan_concept_progress(concept_id);

-- Plan sharing and collaboration
CREATE TABLE learning_plan_collaborators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learning_plan_id UUID NOT NULL REFERENCES learning_plans(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Permission level
    role VARCHAR(20) DEFAULT 'viewer', -- owner, editor, viewer

    -- Sharing
    invited_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    invited_at TIMESTAMPTZ DEFAULT NOW(),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(learning_plan_id, user_id)
);

CREATE INDEX idx_plan_collaborators_plan ON learning_plan_collaborators(learning_plan_id);
CREATE INDEX idx_plan_collaborators_user ON learning_plan_collaborators(user_id);

-- RLS Policies for learning plans
ALTER TABLE learning_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_plan_concepts ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_learning_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_plan_concept_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_plan_collaborators ENABLE ROW LEVEL SECURITY;

-- Public plans are visible to all
CREATE POLICY learning_plans_public_select ON learning_plans
    FOR SELECT USING (is_public = true AND is_published = true);

-- Creators can manage their own plans
CREATE POLICY learning_plans_creator_all ON learning_plans
    FOR ALL USING (auth.uid() = created_by);

-- Collaborators can view/edit based on role
CREATE POLICY learning_plans_collaborators_select ON learning_plans
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM learning_plan_collaborators
            WHERE learning_plan_id = id AND user_id = auth.uid()
        )
    );

-- Plan concepts inherit plan visibility
CREATE POLICY plan_concepts_select ON learning_plan_concepts
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM learning_plans
            WHERE id = learning_plan_id AND (is_public = true OR created_by = auth.uid())
        )
    );

-- Users can only see their own enrollments
CREATE POLICY user_learning_plans_policy ON user_learning_plans
    FOR ALL USING (auth.uid() = user_id);

-- Users can only see their own progress
CREATE POLICY user_plan_progress_policy ON user_plan_concept_progress
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_learning_plans
            WHERE id = user_learning_plan_id AND user_id = auth.uid()
        )
    );

-- Function to update plan enrollment count
CREATE OR REPLACE FUNCTION update_plan_enrollment_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE learning_plans
        SET enrollment_count = enrollment_count + 1
        WHERE id = NEW.learning_plan_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE learning_plans
        SET enrollment_count = GREATEST(0, enrollment_count - 1)
        WHERE id = OLD.learning_plan_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_enrollment_count_trigger
AFTER INSERT OR DELETE ON user_learning_plans
FOR EACH ROW EXECUTE FUNCTION update_plan_enrollment_count();

-- Function to update plan completion count
CREATE OR REPLACE FUNCTION update_plan_completion_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND (OLD IS NULL OR OLD.status != 'completed') THEN
        UPDATE learning_plans
        SET completion_count = completion_count + 1
        WHERE id = NEW.learning_plan_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_completion_count_trigger
AFTER INSERT OR UPDATE ON user_learning_plans
FOR EACH ROW EXECUTE FUNCTION update_plan_completion_count();

-- Function to calculate and update plan progress
CREATE OR REPLACE FUNCTION update_user_plan_progress()
RETURNS TRIGGER AS $$
DECLARE
    total_concepts INTEGER;
    completed_concepts INTEGER;
    progress DECIMAL(5, 2);
BEGIN
    -- Get total concepts in plan
    SELECT COUNT(*) INTO total_concepts
    FROM learning_plan_concepts
    WHERE learning_plan_id = (
        SELECT learning_plan_id FROM user_learning_plans WHERE id = NEW.user_learning_plan_id
    );

    -- Get completed concepts
    SELECT COUNT(*) INTO completed_concepts
    FROM user_plan_concept_progress
    WHERE user_learning_plan_id = NEW.user_learning_plan_id
    AND is_completed = true;

    -- Calculate progress percentage
    IF total_concepts > 0 THEN
        progress := (completed_concepts::DECIMAL / total_concepts::DECIMAL) * 100;
    ELSE
        progress := 0;
    END IF;

    -- Update user learning plan
    UPDATE user_learning_plans
    SET
        completed_concept_count = completed_concepts,
        total_concept_count = total_concepts,
        progress_percentage = progress,
        status = CASE
            WHEN progress >= 100 THEN 'completed'
            WHEN progress > 0 THEN 'active'
            ELSE status
        END,
        completed_at = CASE
            WHEN progress >= 100 AND completed_at IS NULL THEN NOW()
            ELSE completed_at
        END
    WHERE id = NEW.user_learning_plan_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_plan_progress_trigger
AFTER INSERT OR UPDATE ON user_plan_concept_progress
FOR EACH ROW EXECUTE FUNCTION update_user_plan_progress();

-- Add triggers for updated_at
CREATE TRIGGER update_learning_plans_updated_at BEFORE UPDATE ON learning_plans
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_plan_concepts_updated_at BEFORE UPDATE ON learning_plan_concepts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_learning_plans_updated_at BEFORE UPDATE ON user_learning_plans
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_plan_concept_progress_updated_at BEFORE UPDATE ON user_plan_concept_progress
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
