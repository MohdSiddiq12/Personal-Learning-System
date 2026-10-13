create table public.topics (
    id uuid primary key default gen_random_uuid(),
    book_id uuid not null references public.books(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    parent_id uuid,
    kind text not null check (kind in ('topic', 'subtopic', 'framework', 'principle', 'method')),
    title text not null check (length(title) between 1 and 160),
    summary text not null check (length(summary) <= 1200),
    importance integer not null check (importance between 1 and 5),
    est_minutes integer not null check (est_minutes between 1 and 240),
    position integer not null check (position >= 0),
    page_refs integer[] not null default '{}',
    unique (id, book_id, user_id),
    foreign key (parent_id, book_id, user_id)
        references public.topics(id, book_id, user_id) on delete cascade
);
create index topics_user_idx on public.topics(user_id);
create index topics_book_idx on public.topics(book_id);
create index topics_parent_idx on public.topics(parent_id);
alter table public.topics enable row level security;
create policy topics_owner_all on public.topics for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create table public.topic_progress (
    user_id uuid not null references auth.users(id) on delete cascade,
    book_id uuid not null references public.books(id) on delete cascade,
    topic_id uuid not null,
    status text not null default 'new' check (status in ('new', 'learning', 'understood', 'review')),
    updated_at timestamptz not null default now(),
    primary key (user_id, topic_id),
    foreign key (topic_id, book_id, user_id)
        references public.topics(id, book_id, user_id) on delete cascade
);
create index topic_progress_user_idx on public.topic_progress(user_id);
create index topic_progress_book_idx on public.topic_progress(book_id);
alter table public.topic_progress enable row level security;
create policy topic_progress_owner_all on public.topic_progress for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create table public.learning_preferences (
    user_id uuid not null references auth.users(id) on delete cascade,
    book_id uuid not null references public.books(id) on delete cascade,
    minutes_per_topic integer not null default 10 check (minutes_per_topic between 1 and 240),
    daily_minutes integer not null default 30 check (daily_minutes between 1 and 1440),
    goal text not null default 'understand' check (goal in ('understand', 'apply', 'review')),
    updated_at timestamptz not null default now(),
    primary key (user_id, book_id)
);
create index learning_preferences_user_idx on public.learning_preferences(user_id);
create index learning_preferences_book_idx on public.learning_preferences(book_id);
alter table public.learning_preferences enable row level security;
create policy learning_preferences_owner_all on public.learning_preferences for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create table public.learning_paths (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    book_id uuid not null references public.books(id) on delete cascade,
    goal text not null check (goal in ('understand', 'apply', 'review')),
    minutes_per_topic integer not null check (minutes_per_topic between 1 and 240),
    daily_minutes integer not null check (daily_minutes between 1 and 1440),
    created_at timestamptz not null default now(),
    unique (id, book_id, user_id)
);
create index learning_paths_user_idx on public.learning_paths(user_id);
create index learning_paths_book_idx on public.learning_paths(book_id);
alter table public.learning_paths enable row level security;
create policy learning_paths_owner_all on public.learning_paths for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create table public.path_items (
    id uuid primary key default gen_random_uuid(),
    path_id uuid not null,
    user_id uuid not null references auth.users(id) on delete cascade,
    book_id uuid not null references public.books(id) on delete cascade,
    topic_id uuid not null,
    position integer not null check (position >= 0),
    day_number integer not null check (day_number >= 1),
    is_optional boolean not null default false,
    unique (path_id, topic_id),
    unique (path_id, position),
    foreign key (path_id, book_id, user_id)
        references public.learning_paths(id, book_id, user_id) on delete cascade,
    foreign key (topic_id, book_id, user_id)
        references public.topics(id, book_id, user_id) on delete cascade
);
create index path_items_user_idx on public.path_items(user_id);
create index path_items_book_idx on public.path_items(book_id);
create index path_items_path_idx on public.path_items(path_id);
alter table public.path_items enable row level security;
create policy path_items_owner_all on public.path_items for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create table public.highlights (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    book_id uuid not null references public.books(id) on delete cascade,
    topic_id uuid,
    page integer not null check (page > 0),
    text text not null check (length(text) between 1 and 4000),
    note text not null default '' check (length(note) <= 1000),
    created_at timestamptz not null default now(),
    foreign key (topic_id, book_id, user_id)
        references public.topics(id, book_id, user_id) on delete set null (topic_id)
);
create index highlights_user_idx on public.highlights(user_id);
create index highlights_book_idx on public.highlights(book_id);
alter table public.highlights enable row level security;
create policy highlights_owner_all on public.highlights for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create table public.notes (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    book_id uuid not null references public.books(id) on delete cascade,
    topic_id uuid,
    body text not null check (length(body) between 1 and 10000),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    foreign key (topic_id, book_id, user_id)
        references public.topics(id, book_id, user_id) on delete set null (topic_id)
);
create index notes_user_idx on public.notes(user_id);
create index notes_book_idx on public.notes(book_id);
create index notes_topic_idx on public.notes(topic_id);
alter table public.notes enable row level security;
create policy notes_owner_all on public.notes for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
