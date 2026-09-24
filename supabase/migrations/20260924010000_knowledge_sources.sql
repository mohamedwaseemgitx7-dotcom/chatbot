-- =====================================================================
-- FarmerAssist — knowledge provenance
-- Every knowledge record must say where it came from and how far it has been verified.
-- =====================================================================
alter table public.knowledge
  add column if not exists external_id          text unique,
  add column if not exists pair_id              text,
  add column if not exists publisher            text,
  add column if not exists source_url           text,
  add column if not exists retrieved_at         timestamptz,
  add column if not exists verification_status text not null default 'official_source_pending_review'
    check (verification_status in ('official_source_pending_review', 'expert_verified'));

-- Only records with a real source may be stored. (Guarded so the file is safe to run more than once.)
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'knowledge_source_url_required') then
    alter table public.knowledge
      add constraint knowledge_source_url_required check (source_url is not null and source_url ~ '^https://');
  end if;
end $$;

create index if not exists knowledge_pair_idx on public.knowledge (pair_id);
