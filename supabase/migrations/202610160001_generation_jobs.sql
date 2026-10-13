create table public.generation_jobs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    book_id uuid not null references public.books(id) on delete cascade,
    topic_id uuid,
    kind text not null check (kind in ('map', 'lesson')),
    status text not null default 'queued'
        check (status in ('queued', 'running', 'done', 'failed')),
    step text not null default 'queued',
    progress_pct integer not null default 0 check (progress_pct between 0 and 100),
    total_chunks integer not null default 0 check (total_chunks >= 0),
    done_chunks integer not null default 0 check (done_chunks >= 0),
    error_code text,
    error_message text,
    consent_at timestamptz not null,
    reserved_tokens integer not null default 0 check (reserved_tokens >= 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    heartbeat_at timestamptz not null default now(),
    estimated_tokens integer not null default 0 check (estimated_tokens >= 0),
    constraint generation_jobs_topic_fk foreign key (topic_id)
        references public.topics(id) on delete cascade
);

create unique index generation_jobs_one_active_user_kind
    on public.generation_jobs(user_id, kind)
    where status in ('queued', 'running');
create index generation_jobs_user_book_idx on public.generation_jobs(user_id, book_id);
create index generation_jobs_status_idx on public.generation_jobs(status);
create index generation_jobs_user_created_idx on public.generation_jobs(user_id, created_at desc);

create table public.job_chunk_results (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.generation_jobs(id) on delete cascade,
    chunk_index integer not null check (chunk_index >= 0),
    payload jsonb not null,
    tokens_in integer not null default 0 check (tokens_in >= 0),
    tokens_out integer not null default 0 check (tokens_out >= 0),
    created_at timestamptz not null default now(),
    unique (job_id, chunk_index)
);
create index job_chunk_results_job_idx on public.job_chunk_results(job_id, chunk_index);

create table public.llm_usage_ledger (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete set null,
    job_id uuid references public.generation_jobs(id) on delete set null,
    tokens_in integer not null check (tokens_in >= 0),
    tokens_out integer not null check (tokens_out >= 0),
    day date not null default (timezone('utc', now())::date),
    created_at timestamptz not null default now()
);
create index llm_usage_user_day_idx on public.llm_usage_ledger(user_id, day);
create index llm_usage_day_idx on public.llm_usage_ledger(day);
create index llm_usage_job_idx on public.llm_usage_ledger(job_id);

alter table public.generation_jobs enable row level security;
create policy generation_jobs_owner_all on public.generation_jobs
    for all to authenticated using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
alter table public.job_chunk_results enable row level security;
create policy job_chunk_results_owner_all on public.job_chunk_results
    for all to authenticated using (
        exists (select 1 from public.generation_jobs j
                where j.id = job_id and j.user_id = (select auth.uid()))
    ) with check (
        exists (select 1 from public.generation_jobs j
                where j.id = job_id and j.user_id = (select auth.uid()))
    );
alter table public.llm_usage_ledger enable row level security;
create policy llm_usage_ledger_owner_all on public.llm_usage_ledger
    for all to authenticated using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

create or replace function public.create_generation_job(
    p_user_id uuid,
    p_book_id uuid,
    p_kind text,
    p_estimated_tokens integer,
    p_daily_token_budget integer,
    p_max_books_per_day integer,
    p_max_lessons_per_day integer,
    p_consent_at timestamptz
) returns public.generation_jobs
language plpgsql security definer set search_path = public
as $$
declare
    created public.generation_jobs;
    used_tokens bigint;
    daily_jobs bigint;
begin
    if p_kind not in ('map', 'lesson') or p_estimated_tokens < 0 then
        raise exception 'invalid_job_request' using errcode = '22023';
    end if;
    perform pg_advisory_xact_lock(hashtextextended('learnbook-generation-budget', 0));
    select coalesce(sum(tokens_in + tokens_out), 0) into used_tokens
      from public.llm_usage_ledger where day = timezone('utc', now())::date;
    select used_tokens + coalesce(sum(reserved_tokens), 0) into used_tokens
      from public.generation_jobs
     where status in ('queued', 'running')
       and created_at::date = timezone('utc', now())::date;
    if used_tokens + p_estimated_tokens > p_daily_token_budget then
        raise exception 'budget_exhausted' using errcode = 'P0001';
    end if;
    if exists (select 1 from public.generation_jobs
               where user_id = p_user_id and kind = p_kind
                 and status in ('queued', 'running')) then
        raise exception 'active_job' using errcode = 'P0001';
    end if;
    select count(*) into daily_jobs from public.generation_jobs
     where user_id = p_user_id and kind = p_kind
       and created_at::date = timezone('utc', now())::date;
    if p_kind = 'map' and daily_jobs >= p_max_books_per_day then
        raise exception 'quota_exceeded' using errcode = 'P0001';
    elsif p_kind = 'lesson' and daily_jobs >= p_max_lessons_per_day then
        raise exception 'quota_exceeded' using errcode = 'P0001';
    end if;
    insert into public.generation_jobs(
        user_id, book_id, kind, consent_at, reserved_tokens, estimated_tokens, total_chunks
    ) values (
        p_user_id, p_book_id, p_kind, p_consent_at, p_estimated_tokens, p_estimated_tokens, 0
    ) returning * into created;
    return created;
end;
$$;

create or replace function public.retry_generation_job(
    p_job_id uuid, p_user_id uuid, p_daily_token_budget integer
)
returns public.generation_jobs
language plpgsql security definer set search_path = public
as $$
declare
    updated public.generation_jobs;
    used_tokens bigint;
begin
    perform pg_advisory_xact_lock(hashtextextended('learnbook-generation-budget', 0));
    if exists (select 1 from public.generation_jobs
               where user_id = p_user_id and kind = (
                   select kind from public.generation_jobs where id = p_job_id and user_id = p_user_id
               ) and status in ('queued', 'running')) then
        raise exception 'active_job' using errcode = 'P0001';
    end if;
    select coalesce(sum(tokens_in + tokens_out), 0) into used_tokens
      from public.llm_usage_ledger where day = timezone('utc', now())::date;
    select used_tokens + coalesce(sum(reserved_tokens), 0) into used_tokens
      from public.generation_jobs
     where status in ('queued', 'running')
       and created_at::date = timezone('utc', now())::date;
    update public.generation_jobs
       set status = 'queued', step = 'queued', progress_pct = 0,
           error_code = null, error_message = null,
           heartbeat_at = now(), updated_at = now(), reserved_tokens = estimated_tokens
     where id = p_job_id and user_id = p_user_id and status = 'failed'
       and used_tokens + estimated_tokens <= p_daily_token_budget
     returning * into updated;
    if not found then
        if exists (select 1 from public.generation_jobs where id = p_job_id and user_id = p_user_id and status = 'failed') then
            raise exception 'budget_exhausted' using errcode = 'P0001';
        end if;
        raise exception 'job_not_retryable' using errcode = 'P0002';
    end if;
    return updated;
end;
$$;

revoke all on function public.create_generation_job(uuid, uuid, text, integer, integer, integer, integer, timestamptz) from public, anon, authenticated;
grant execute on function public.create_generation_job(uuid, uuid, text, integer, integer, integer, integer, timestamptz) to service_role;
revoke all on function public.retry_generation_job(uuid, uuid, integer) from public, anon, authenticated;
grant execute on function public.retry_generation_job(uuid, uuid, integer) to service_role;
