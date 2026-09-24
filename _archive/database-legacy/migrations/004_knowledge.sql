-- Migration 004: Agricultural Knowledge Table
CREATE TABLE IF NOT EXISTS public.knowledge (
    id VARCHAR(100) PRIMARY KEY,
    crop VARCHAR(50) NOT NULL,
    topic VARCHAR(100) NOT NULL,
    subtopic VARCHAR(100),
    language VARCHAR(20) DEFAULT 'english',
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(255) DEFAULT 'TNAU Agritech',
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.knowledge ENABLE ROW LEVEL SECURITY;
