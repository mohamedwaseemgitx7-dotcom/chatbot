-- Migration 005: Image Disease Predictions Table
CREATE TABLE IF NOT EXISTS public.image_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES public.messages(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    crop VARCHAR(50) NOT NULL,
    prediction VARCHAR(100) NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL,
    symptoms JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.image_predictions ENABLE ROW LEVEL SECURITY;
