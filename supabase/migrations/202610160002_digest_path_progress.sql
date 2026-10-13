alter table public.topics
    add column key_terms text[] not null default '{}',
    add column support text not null default 'ok'
        check (support in ('ok', 'weak'));

alter table public.learning_preferences
    alter column daily_minutes set default 30,
    add constraint learning_preferences_daily_minutes_task8_check
        check (daily_minutes between 5 and 180);
alter table public.path_items
    add column minutes_allocated integer not null default 0 check (minutes_allocated >= 0),
    add column is_condensed boolean not null default false,
    add column completed_at timestamptz;

alter table public.lessons drop constraint lessons_user_id_topic_id_key;
alter table public.lessons
    add column target_minutes integer not null default 10
        check (target_minutes in (5, 10));
alter table public.lessons
    add constraint lessons_user_topic_target_unique
    unique (user_id, topic_id, target_minutes);

create table public.daily_digests (
    book_id uuid primary key references public.books(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    body text not null,
    structure_source text not null check (structure_source in ('outline', 'headings', 'windows', 'fallback')),
    sections_total integer not null check (sections_total >= 0),
    sections_covered integer not null check (sections_covered >= 0),
    pages_covered integer not null check (pages_covered >= 0),
    created_at timestamptz not null default now()
);
create index daily_digests_user_idx on public.daily_digests(user_id);
alter table public.daily_digests enable row level security;
create policy daily_digests_owner_all on public.daily_digests
    for all to authenticated using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create table public.book_outlines (
    book_id uuid primary key references public.books(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    sections jsonb not null default '[]'::jsonb,
    structure_source text not null check (structure_source in ('outline', 'headings', 'windows', 'fallback')),
    created_at timestamptz not null default now()
);
create index book_outlines_user_idx on public.book_outlines(user_id);
alter table public.book_outlines enable row level security;
create policy book_outlines_owner_all on public.book_outlines
    for all to authenticated using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
