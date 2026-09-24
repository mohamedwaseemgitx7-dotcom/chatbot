-- =====================================================================
-- FarmerAssist — initial Supabase schema
--   Tables, foreign keys, indexes, Row Level Security, Storage buckets + policies.
--   Run ONCE, on an empty project (Supabase SQL Editor or `supabase db push`).
--   Already applied? Don't re-run it (error 42P07 "relation already exists") — run only the later migrations.
--
-- Identity: every browser gets a Supabase Auth user (anonymous sign-in today,
-- email/phone login later). public.users is that user's profile row.
-- Private data is reachable only by its owner: auth.uid() = owner.
-- The backend uses the secret (service-role) key, which bypasses RLS — never ship it to the browser.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Shared helpers
-- ---------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------
-- users: one profile per auth user (created automatically on sign-up)
-- ---------------------------------------------------------------------
create table public.users (
  id          uuid primary key references auth.users (id) on delete cascade,
  email       text,
  name        text check (char_length(name) <= 120),
  language    text not null default 'english' check (language in ('english', 'tamil', 'tanglish')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create trigger users_set_updated_at
  before update on public.users
  for each row execute function public.set_updated_at();

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.users (id, email) values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_auth_user();

-- Users created before this migration also get a profile.
insert into public.users (id, email)
select id, email from auth.users
on conflict (id) do nothing;

-- ---------------------------------------------------------------------
-- conversations
-- ---------------------------------------------------------------------
create table public.conversations (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references public.users (id) on delete cascade,
  title       text not null default 'New conversation' check (char_length(title) between 1 and 200),
  language    text check (language in ('english', 'tamil', 'tanglish')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Sidebar query: "my conversations, most recent first".
create index conversations_user_updated_idx on public.conversations (user_id, updated_at desc);

create trigger conversations_set_updated_at
  before update on public.conversations
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------
-- messages (immutable once written)
-- ---------------------------------------------------------------------
create table public.messages (
  id               uuid primary key default gen_random_uuid(),
  conversation_id  uuid not null references public.conversations (id) on delete cascade,
  sender           text not null check (sender in ('user', 'assistant', 'system')),
  message          text not null default '' check (char_length(message) <= 8000),
  language         text check (language in ('english', 'tamil', 'tanglish')),
  intent           text check (char_length(intent) <= 100),
  confidence       double precision check (confidence between 0 and 1),
  message_type     text not null default 'text' check (message_type in ('text', 'image', 'voice', 'system')),
  -- Structured payloads the UI renders as components (photo details, analysis card). Never shown raw.
  metadata         jsonb not null default '{}'::jsonb,
  created_at       timestamptz not null default now()
);

-- Loading one conversation in order (also serves the FK / cascade lookup).
create index messages_conversation_created_idx on public.messages (conversation_id, created_at);
-- messages.language / messages.intent: no query filters on them yet — add indexes with the analytics that need them.

-- A new message moves its conversation to the top of the list.
create or replace function public.touch_conversation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.conversations set updated_at = now() where id = new.conversation_id;
  return new;
end;
$$;

create trigger messages_touch_conversation
  after insert on public.messages
  for each row execute function public.touch_conversation();

-- ---------------------------------------------------------------------
-- knowledge: agricultural reference content for RAG (public, read-only)
-- Schema only — populate from verified sources through the backend.
-- ---------------------------------------------------------------------
create table public.knowledge (
  id                     uuid primary key default gen_random_uuid(),
  crop                   text not null,
  topic                  text not null,
  subtopic               text,
  language               text not null default 'english' check (language in ('english', 'tamil', 'tanglish')),
  title                  text not null,
  content                text not null,
  keywords               text[] not null default '{}',
  source                 text,
  verification_required  boolean not null default true,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

create index knowledge_crop_topic_idx on public.knowledge (crop, topic);
create index knowledge_language_idx on public.knowledge (language);

create trigger knowledge_set_updated_at
  before update on public.knowledge
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------
-- image_predictions: AI output for a user's photo message (a preliminary prediction, not a diagnosis)
-- ---------------------------------------------------------------------
create table public.image_predictions (
  id          uuid primary key default gen_random_uuid(),
  message_id  uuid not null references public.messages (id) on delete cascade,
  image_url   text not null,          -- Storage object path in farmer-images, not a public URL
  crop        text,
  prediction  text,
  confidence  double precision check (confidence between 0 and 1),
  status      text not null default 'processing' check (status in ('processing', 'completed', 'failed')),
  created_at  timestamptz not null default now()
);

create index image_predictions_message_idx on public.image_predictions (message_id);

-- ---------------------------------------------------------------------
-- voice_transcriptions
-- ---------------------------------------------------------------------
create table public.voice_transcriptions (
  id          uuid primary key default gen_random_uuid(),
  message_id  uuid not null references public.messages (id) on delete cascade,
  audio_url   text,                   -- Storage object path in farmer-audio
  transcript  text,
  language    text check (language in ('english', 'tamil', 'tanglish')),
  confidence  double precision check (confidence between 0 and 1),
  status      text not null default 'processing' check (status in ('processing', 'completed', 'failed')),
  created_at  timestamptz not null default now()
);

create index voice_transcriptions_message_idx on public.voice_transcriptions (message_id);

-- ---------------------------------------------------------------------
-- feedback: one rating per user per message
-- ---------------------------------------------------------------------
create table public.feedback (
  id             uuid primary key default gen_random_uuid(),
  message_id     uuid not null references public.messages (id) on delete cascade,
  user_id        uuid not null default auth.uid() references public.users (id) on delete cascade,
  rating         integer not null check (rating between 1 and 5),
  feedback_text  text check (char_length(feedback_text) <= 2000),
  created_at     timestamptz not null default now(),
  unique (message_id, user_id)
);

create index feedback_message_idx on public.feedback (message_id);
create index feedback_user_idx on public.feedback (user_id);

-- ---------------------------------------------------------------------
-- rate_limit_logs: backend-only. Stores a salted hash of the IP, never the raw address.
-- ---------------------------------------------------------------------
create table public.rate_limit_logs (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid references public.users (id) on delete set null,
  ip_hash        text check (char_length(ip_hash) <= 128),
  endpoint       text not null,
  request_count  integer not null default 1 check (request_count > 0),
  window_start   timestamptz not null,
  created_at     timestamptz not null default now()
);

create index rate_limit_logs_lookup_idx on public.rate_limit_logs (endpoint, ip_hash, window_start desc);
create index rate_limit_logs_user_idx on public.rate_limit_logs (user_id);

-- =====================================================================
-- Row Level Security
-- (select auth.uid()) is evaluated once per query instead of once per row.
-- =====================================================================
alter table public.users                enable row level security;
alter table public.conversations        enable row level security;
alter table public.messages             enable row level security;
alter table public.knowledge            enable row level security;
alter table public.image_predictions    enable row level security;
alter table public.voice_transcriptions enable row level security;
alter table public.feedback             enable row level security;
alter table public.rate_limit_logs      enable row level security;

-- Ownership check shared by message-level tables.
-- Parameters are prefixed with p_ so they can never be confused with column names.
create or replace function public.owns_conversation(p_conversation_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.conversations c
    where c.id = p_conversation_id and c.user_id = (select auth.uid())
  );
$$;

create or replace function public.owns_message(p_message_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.messages m
    join public.conversations c on c.id = m.conversation_id
    where m.id = p_message_id and c.user_id = (select auth.uid())
  );
$$;

-- users: read and edit your own profile (rows are created by the auth trigger)
create policy "users: read own profile" on public.users
  for select to authenticated using (id = (select auth.uid()));
create policy "users: update own profile" on public.users
  for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));

-- conversations: full control over your own
create policy "conversations: read own" on public.conversations
  for select to authenticated using (user_id = (select auth.uid()));
create policy "conversations: create own" on public.conversations
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy "conversations: update own" on public.conversations
  for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy "conversations: delete own" on public.conversations
  for delete to authenticated using (user_id = (select auth.uid()));

-- messages: read/add in your own conversations; no edits (deleted with the conversation)
create policy "messages: read in own conversations" on public.messages
  for select to authenticated using (public.owns_conversation(conversation_id));
create policy "messages: add to own conversations" on public.messages
  for insert to authenticated with check (public.owns_conversation(conversation_id));

-- image_predictions / voice_transcriptions: through message ownership
create policy "image_predictions: read own" on public.image_predictions
  for select to authenticated using (public.owns_message(message_id));
create policy "image_predictions: add own" on public.image_predictions
  for insert to authenticated with check (public.owns_message(message_id));

create policy "voice_transcriptions: read own" on public.voice_transcriptions
  for select to authenticated using (public.owns_message(message_id));
create policy "voice_transcriptions: add own" on public.voice_transcriptions
  for insert to authenticated with check (public.owns_message(message_id));

-- feedback: yours, on messages you own
create policy "feedback: read own" on public.feedback
  for select to authenticated using (user_id = (select auth.uid()));
create policy "feedback: add own" on public.feedback
  for insert to authenticated with check (user_id = (select auth.uid()) and public.owns_message(message_id));
create policy "feedback: update own" on public.feedback
  for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

-- knowledge: public reference data — anyone may read; only the backend (service role) writes
create policy "knowledge: public read" on public.knowledge
  for select to anon, authenticated using (true);

-- rate_limit_logs: no policies → only the service role can touch it
revoke all on public.rate_limit_logs from anon, authenticated;

-- Helper functions are for policies, not for calling over the API.
revoke execute on function public.owns_conversation(uuid) from public, anon;
revoke execute on function public.owns_message(uuid) from public, anon;
revoke execute on function public.handle_new_auth_user() from public, anon, authenticated;
revoke execute on function public.touch_conversation() from public, anon, authenticated;

-- =====================================================================
-- Storage — private buckets; paths are <user_id>/<conversation_id>/<uuid>.<ext>
-- Size and MIME limits are enforced by Storage itself.
-- =====================================================================
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('farmer-images', 'farmer-images', false, 5242880,  array['image/jpeg', 'image/png', 'image/webp']),
  ('farmer-audio',  'farmer-audio',  false, 10485760, array['audio/webm', 'audio/ogg', 'audio/mp4', 'audio/mpeg', 'audio/wav'])
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create policy "farmer files: upload to own conversation folder" on storage.objects
  for insert to authenticated with check (
    bucket_id in ('farmer-images', 'farmer-audio')
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and public.owns_conversation(((storage.foldername(name))[2])::uuid)
    and (
      (bucket_id = 'farmer-images' and lower(storage.extension(name)) in ('jpg', 'jpeg', 'png', 'webp'))
      or (bucket_id = 'farmer-audio' and lower(storage.extension(name)) in ('webm', 'ogg', 'm4a', 'mp3', 'wav'))
    )
  );

create policy "farmer files: read own" on storage.objects
  for select to authenticated using (
    bucket_id in ('farmer-images', 'farmer-audio')
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy "farmer files: delete own" on storage.objects
  for delete to authenticated using (
    bucket_id in ('farmer-images', 'farmer-audio')
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );
-- No update policy: uploaded files are never overwritten in place.
