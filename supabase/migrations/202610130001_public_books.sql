create extension if not exists pgcrypto;

create table if not exists public.books (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text,
    author text,
    page_count integer not null check (page_count > 0),
    file_size_bytes bigint not null check (file_size_bytes > 0),
    needs_ocr boolean not null default false,
    sha256 text not null check (length(sha256) = 64),
    storage_path text not null unique,
    summary_json jsonb,
    created_at timestamptz not null default now(),
    unique (user_id, sha256)
);

create table if not exists public.book_pages (
    id bigint generated always as identity primary key,
    book_id uuid not null references public.books(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    page_number integer not null check (page_number > 0),
    text text not null,
    char_count integer not null check (char_count >= 0),
    is_empty boolean not null,
    has_images boolean not null,
    unique (book_id, page_number)
);

create index if not exists books_user_created_idx
    on public.books (user_id, created_at desc);
create index if not exists book_pages_book_page_idx
    on public.book_pages (book_id, page_number);

alter table public.books enable row level security;
alter table public.book_pages enable row level security;

create policy "owners can read books"
    on public.books for select to authenticated
    using ((select auth.uid()) = user_id);
create policy "owners can insert books"
    on public.books for insert to authenticated
    with check ((select auth.uid()) = user_id);
create policy "owners can update books"
    on public.books for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
create policy "owners can delete books"
    on public.books for delete to authenticated
    using ((select auth.uid()) = user_id);

create policy "owners can read book pages"
    on public.book_pages for select to authenticated
    using ((select auth.uid()) = user_id);
create policy "owners can insert book pages"
    on public.book_pages for insert to authenticated
    with check ((select auth.uid()) = user_id);
create policy "owners can delete book pages"
    on public.book_pages for delete to authenticated
    using ((select auth.uid()) = user_id);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('book-pdfs', 'book-pdfs', false, 52428800, array['application/pdf'])
on conflict (id) do update set
    public = false,
    file_size_limit = 52428800,
    allowed_mime_types = array['application/pdf'];

create policy "owners can upload private book PDFs"
    on storage.objects for insert to authenticated
    with check (
        bucket_id = 'book-pdfs'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );
create policy "owners can read private book PDFs"
    on storage.objects for select to authenticated
    using (
        bucket_id = 'book-pdfs'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );
create policy "owners can delete private book PDFs"
    on storage.objects for delete to authenticated
    using (
        bucket_id = 'book-pdfs'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

create table if not exists public.ai_usage (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    created_at timestamptz not null default now()
);
create index if not exists ai_usage_user_created_idx
    on public.ai_usage (user_id, created_at desc);
alter table public.ai_usage enable row level security;

create table if not exists public.upload_usage (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    created_at timestamptz not null default now()
);
create index if not exists upload_usage_user_created_idx
    on public.upload_usage (user_id, created_at desc);
alter table public.upload_usage enable row level security;

create or replace function public.reserve_book_upload(
    p_user_id uuid,
    p_daily_limit integer
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    user_daily_count integer;
begin
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtext('learnbook-upload-quota-' || p_user_id::text)
    );

    select count(*) into user_daily_count
    from public.upload_usage
    where user_id = p_user_id
      and created_at >= date_trunc('day', now());

    if user_daily_count >= p_daily_limit then
        return false;
    end if;

    insert into public.upload_usage (user_id) values (p_user_id);
    return true;
end;
$$;

revoke all on function public.reserve_book_upload(uuid, integer)
    from public, anon, authenticated;
grant execute on function public.reserve_book_upload(uuid, integer)
    to service_role;

create or replace function public.reserve_book_summary(
    p_user_id uuid,
    p_daily_limit integer,
    p_monthly_limit integer
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    user_daily_count integer;
    global_month_count integer;
begin
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtext('learnbook-summary-quota')
    );

    select count(*) into user_daily_count
    from public.ai_usage
    where user_id = p_user_id
      and created_at >= date_trunc('day', now());

    select count(*) into global_month_count
    from public.ai_usage
    where created_at >= date_trunc('month', now());

    if user_daily_count >= p_daily_limit or global_month_count >= p_monthly_limit then
        return false;
    end if;

    insert into public.ai_usage (user_id) values (p_user_id);
    return true;
end;
$$;

revoke all on function public.reserve_book_summary(uuid, integer, integer)
    from public, anon, authenticated;
grant execute on function public.reserve_book_summary(uuid, integer, integer)
    to service_role;