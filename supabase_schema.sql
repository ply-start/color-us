-- Run this in Supabase SQL Editor.

create table if not exists public.color_us_invites (
  token text primary key,
  image_path text not null,
  a_temperature integer not null check (a_temperature between -100 and 100),
  a_saturation integer not null check (a_saturation between 0 and 200),
  a_brightness integer not null check (a_brightness between 0 and 200),
  created_at timestamptz not null default now()
);

alter table public.color_us_invites enable row level security;

drop policy if exists "public read invites" on public.color_us_invites;
create policy "public read invites"
on public.color_us_invites
for select
to anon
using (true);

drop policy if exists "public insert invites" on public.color_us_invites;
create policy "public insert invites"
on public.color_us_invites
for insert
to anon
with check (true);

-- Create a public Storage bucket named color-us-photos in Storage UI first.
-- Then run these policies. If your bucket name is different, update bucket_id.

drop policy if exists "public read color us photos" on storage.objects;
create policy "public read color us photos"
on storage.objects
for select
to anon
using (bucket_id = 'color-us-photos');

drop policy if exists "public upload color us photos" on storage.objects;
create policy "public upload color us photos"
on storage.objects
for insert
to anon
with check (bucket_id = 'color-us-photos');
