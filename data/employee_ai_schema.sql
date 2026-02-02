-- Create employee_personas table
CREATE TABLE IF NOT EXISTS employee_personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    role TEXT,
    expertise TEXT,
    evaluation_perspective TEXT,
    personality_traits TEXT,
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create employee_feedback table
CREATE TABLE IF NOT EXISTS employee_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID REFERENCES employee_personas(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL,
    ai_evaluation TEXT,
    user_feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS (Service key will bypass this)
ALTER TABLE employee_personas ENABLE ROW LEVEL SECURITY;
ALTER TABLE employee_feedback ENABLE ROW LEVEL SECURITY;

-- Allow all for testing (or configure as needed for your project)
CREATE POLICY "Public Read Access" ON employee_personas FOR SELECT USING (true);
CREATE POLICY "Public Read Access" ON employee_feedback FOR SELECT USING (true);
