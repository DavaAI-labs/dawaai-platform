-- ============================================================
-- DavaAI v3 — Supabase Schema
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- ============================================================

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ── PHARMACIES ──────────────────────────────────────────────
-- Each pharmacy is a separate tenant. Auth users are linked here.
create table pharmacies (
  id            uuid primary key default uuid_generate_v4(),
  name          text not null,
  owner_name    text not null,
  phone         text,
  address       text,
  license_no    text,
  created_at    timestamptz default now()
);

-- ── PROFILES ────────────────────────────────────────────────
-- One profile per Supabase auth user, linked to a pharmacy.
create table profiles (
  id            uuid primary key references auth.users on delete cascade,
  pharmacy_id   uuid references pharmacies(id) on delete cascade,
  full_name     text,
  role          text default 'owner',  -- 'owner' | 'staff'
  created_at    timestamptz default now()
);

-- ── SUPPLIERS ───────────────────────────────────────────────
create table suppliers (
  id            uuid primary key default uuid_generate_v4(),
  pharmacy_id   uuid references pharmacies(id) on delete cascade not null,
  name          text not null,
  contact_name  text,
  phone         text,
  email         text,
  address       text,
  created_at    timestamptz default now()
);

-- ── INVENTORY ───────────────────────────────────────────────
-- Core table: one row per medicine batch in stock.
create table inventory (
  id              uuid primary key default uuid_generate_v4(),
  pharmacy_id     uuid references pharmacies(id) on delete cascade not null,
  supplier_id     uuid references suppliers(id) on delete set null,

  -- Medicine identity
  brand_name      text not null,
  generic_name    text not null,
  strength        text,                   -- e.g. "500 mg"
  form            text,                   -- Tablet / Capsule / Syrup
  manufacturer    text,
  barcode         text,

  -- Stock
  quantity        integer not null default 0,
  low_stock_threshold integer default 10, -- alert when quantity <= this

  -- Pricing
  purchase_price  numeric(10,2),          -- cost to pharmacy
  mrp             numeric(10,2),          -- printed MRP
  margin_pct      numeric(5,2)            -- auto-computed: ((mrp-purchase)/purchase)*100

    generated always as (
      case when purchase_price > 0
        then round(((mrp - purchase_price) / purchase_price) * 100, 2)
      else null end
    ) stored,

  -- Batch / Expiry
  batch_number    text,
  expiry_date     date not null,

  -- Metadata
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- ── BILLS ───────────────────────────────────────────────────
create table bills (
  id              uuid primary key default uuid_generate_v4(),
  pharmacy_id     uuid references pharmacies(id) on delete cascade not null,
  bill_number     text not null,          -- e.g. "BC-A3F2"
  source          text default 'manual',  -- 'prescription' | 'barcode' | 'manual'
  patient_name    text,
  total_mrp       numeric(10,2),
  total_items     integer,
  created_at      timestamptz default now()
);

-- ── BILL ITEMS ──────────────────────────────────────────────
create table bill_items (
  id              uuid primary key default uuid_generate_v4(),
  bill_id         uuid references bills(id) on delete cascade not null,
  inventory_id    uuid references inventory(id) on delete set null,
  brand_name      text not null,
  generic_name    text,
  strength        text,
  quantity        integer not null,
  mrp             numeric(10,2),
  line_total      numeric(10,2)
    generated always as (mrp * quantity) stored
);

-- ── PRESCRIPTION SCANS ──────────────────────────────────────
create table prescription_scans (
  id              uuid primary key default uuid_generate_v4(),
  pharmacy_id     uuid references pharmacies(id) on delete cascade not null,
  bill_id         uuid references bills(id) on delete set null,
  raw_ocr_text    text,
  image_url       text,
  confidence_avg  numeric(5,2),
  flagged_count   integer default 0,      -- medicines auto-picked but flagged
  created_at      timestamptz default now()
);

-- ── EXPIRY ALERTS VIEW ──────────────────────────────────────
-- Returns medicines expiring within 3 months, tagged critical (<1m) or warning (<3m)
create or replace view expiry_alerts as
  select
    i.*,
    p.name as pharmacy_name,
    case
      when i.expiry_date <= current_date + interval '1 month'  then 'critical'
      when i.expiry_date <= current_date + interval '3 months' then 'warning'
    end as alert_level,
    (i.expiry_date - current_date) as days_until_expiry
  from inventory i
  join pharmacies p on p.id = i.pharmacy_id
  where i.expiry_date <= current_date + interval '3 months'
    and i.quantity > 0
  order by i.expiry_date asc;

-- ── LOW STOCK VIEW ──────────────────────────────────────────
create or replace view low_stock_alerts as
  select
    i.*,
    p.name as pharmacy_name
  from inventory i
  join pharmacies p on p.id = i.pharmacy_id
  where i.quantity <= i.low_stock_threshold
  order by i.quantity asc;

-- ── ROW LEVEL SECURITY ──────────────────────────────────────
-- Each pharmacy can only see its own data.

alter table pharmacies     enable row level security;
alter table profiles       enable row level security;
alter table suppliers      enable row level security;
alter table inventory      enable row level security;
alter table bills          enable row level security;
alter table bill_items     enable row level security;
alter table prescription_scans enable row level security;

-- Helper function: get current user's pharmacy_id
create or replace function my_pharmacy_id()
returns uuid language sql stable as $$
  select pharmacy_id from profiles where id = auth.uid()
$$;

-- Policies
create policy "pharmacy_self" on pharmacies
  for all using (id = my_pharmacy_id());

create policy "profile_self" on profiles
  for all using (id = auth.uid());

create policy "supplier_own" on suppliers
  for all using (pharmacy_id = my_pharmacy_id());

create policy "inventory_own" on inventory
  for all using (pharmacy_id = my_pharmacy_id());

create policy "bills_own" on bills
  for all using (pharmacy_id = my_pharmacy_id());

create policy "bill_items_own" on bill_items
  for all using (
    bill_id in (select id from bills where pharmacy_id = my_pharmacy_id())
  );

create policy "scans_own" on prescription_scans
  for all using (pharmacy_id = my_pharmacy_id());

-- ── AUTO-UPDATE updated_at ───────────────────────────────────
create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

create trigger inventory_updated_at
  before update on inventory
  for each row execute function update_updated_at();