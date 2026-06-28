-- ============================================================
-- DavaAI v4 — Supabase Schema
-- Changes from v3:
--   + decrement_stock() RPC  — atomic, race-condition-safe stock update
--   + corrections table      — persists pharmacist feedback from /api/corrections
--   + index on inventory(pharmacy_id, barcode) for fast barcode lookups
--   + index on inventory(pharmacy_id, expiry_date) for expiry view performance
-- ============================================================

create extension if not exists "uuid-ossp";

-- ── PHARMACIES ──────────────────────────────────────────────
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
create table inventory (
  id              uuid primary key default uuid_generate_v4(),
  pharmacy_id     uuid references pharmacies(id) on delete cascade not null,
  supplier_id     uuid references suppliers(id) on delete set null,

  brand_name      text not null,
  generic_name    text not null,
  strength        text,
  form            text,
  manufacturer    text,
  barcode         text,

  quantity        integer not null default 0 check (quantity >= 0),
  low_stock_threshold integer default 10,

  purchase_price  numeric(10,2),
  mrp             numeric(10,2),
  margin_pct      numeric(5,2)
    generated always as (
      case when purchase_price > 0
        then round(((mrp - purchase_price) / purchase_price) * 100, 2)
      else null end
    ) stored,

  batch_number    text,
  expiry_date     date not null,

  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- Fast barcode lookups (barcode_routes.py: GET /api/barcode/{barcode})
create index if not exists idx_inventory_pharmacy_barcode
  on inventory (pharmacy_id, barcode)
  where barcode is not null;

-- Fast expiry/low-stock view scans
create index if not exists idx_inventory_pharmacy_expiry
  on inventory (pharmacy_id, expiry_date);

create index if not exists idx_inventory_pharmacy_quantity
  on inventory (pharmacy_id, quantity);

-- ── BILLS ───────────────────────────────────────────────────
create table bills (
  id              uuid primary key default uuid_generate_v4(),
  pharmacy_id     uuid references pharmacies(id) on delete cascade not null,
  bill_number     text not null,
  source          text default 'manual',
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
  flagged_count   integer default 0,
  created_at      timestamptz default now()
);

-- ── CORRECTIONS ─────────────────────────────────────────────
-- Pharmacist feedback: every edit a chemist makes is a training pair.
-- Used by /api/corrections endpoint; powers the flywheel.
create table corrections (
  id              uuid primary key default uuid_generate_v4(),
  pharmacy_id     uuid references pharmacies(id) on delete cascade,
  scan_id         text,                        -- short scan reference (e.g. "A3F9BC")
  inventory_id    uuid references inventory(id) on delete set null,
  ocr_raw         text not null,               -- what Vision OCR produced
  corrected_to    text not null,               -- what the pharmacist typed
  brand_name      text,
  generic_name    text,
  strength        text,
  timestamp       timestamptz default now()
);

create index if not exists idx_corrections_pharmacy
  on corrections (pharmacy_id);

-- ── EXPIRY ALERTS VIEW ──────────────────────────────────────
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
alter table pharmacies         enable row level security;
alter table profiles           enable row level security;
alter table suppliers          enable row level security;
alter table inventory          enable row level security;
alter table bills              enable row level security;
alter table bill_items         enable row level security;
alter table prescription_scans enable row level security;
alter table corrections        enable row level security;

create or replace function my_pharmacy_id()
returns uuid language sql stable as $$
  select pharmacy_id from profiles where id = auth.uid()
$$;

create policy "pharmacy_self"   on pharmacies     for all using (id = my_pharmacy_id());
create policy "profile_self"    on profiles       for all using (id = auth.uid());
create policy "supplier_own"    on suppliers      for all using (pharmacy_id = my_pharmacy_id());
create policy "inventory_own"   on inventory      for all using (pharmacy_id = my_pharmacy_id());
create policy "bills_own"       on bills          for all using (pharmacy_id = my_pharmacy_id());
create policy "corrections_own" on corrections    for all using (pharmacy_id = my_pharmacy_id());

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

-- ── ATOMIC STOCK DECREMENT ───────────────────────────────────
-- Called by barcode_routes.py via POST /rest/v1/rpc/decrement_stock
--
-- Why this matters: without this, the backend does two round-trips:
--   1. SELECT quantity FROM inventory WHERE id = $1
--   2. UPDATE inventory SET quantity = $old - $amount WHERE id = $1
-- Under concurrent requests (two pharmacists selling the same medicine)
-- both reads can see the same pre-decrement value, causing oversell.
--
-- This function is a single atomic UPDATE with a WHERE guard.
-- It returns the new quantity on success, or NULL if stock was insufficient.
-- The backend treats NULL as "insufficient stock" and logs the event.

create or replace function decrement_stock(item_id uuid, amount integer)
returns integer
language plpgsql
security definer   -- runs as the function owner, bypasses RLS for the UPDATE
as $$
declare
  new_qty integer;
begin
  update inventory
  set    quantity = quantity - amount
  where  id       = item_id
    and  quantity >= amount   -- guard: never go negative
  returning quantity into new_qty;

  return new_qty;  -- NULL if the WHERE clause matched no rows (insufficient stock)
end;
$$;

-- Grant execute to the service role only (called server-side)
-- The anon/authenticated roles must NOT call this directly.
revoke execute on function decrement_stock(uuid, integer) from public, anon, authenticated;
grant  execute on function decrement_stock(uuid, integer) to service_role;
