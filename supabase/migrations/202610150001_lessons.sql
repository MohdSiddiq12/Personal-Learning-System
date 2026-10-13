create table public.lessons (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    topic_id uuid not null,
    book_id uuid not null references public.books(id) on delete cascade,
    body text not null check (length(body) between 1 and 10000),
    recall_questions jsonb not null check (
        case
            when jsonb_typeof(recall_questions) = 'array'
                then jsonb_array_length(recall_questions) = 2
            else false
        end
    ),
    action text not null check (length(action) between 1 and 1000),
    created_at timestamptz not null default now(),
    unique (user_id, topic_id),
    foreign key (topic_id, book_id, user_id)
        references public.topics(id, book_id, user_id) on delete cascade
);

create index lessons_user_idx on public.lessons(user_id);
create index lessons_book_idx on public.lessons(book_id);
create index lessons_topic_idx on public.lessons(topic_id);
alter table public.lessons enable row level security;
create policy lessons_owner_all on public.lessons for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
