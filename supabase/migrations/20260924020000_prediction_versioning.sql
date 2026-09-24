-- =====================================================================
-- FarmerAssist — record which model produced each photo prediction
-- (lets you debug a prediction months later: model + dataset version + time).
-- =====================================================================
alter table public.image_predictions
  add column if not exists model_name      text,
  add column if not exists model_version   text,
  add column if not exists dataset_version text;

create index if not exists image_predictions_model_version_idx on public.image_predictions (model_version);
