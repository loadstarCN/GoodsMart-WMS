-- Run the entire script in the production warehouse database as the enum owner.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DO $check$
BEGIN
    IF current_database() <> 'warehouse' THEN
        RAISE EXCEPTION 'Expected database warehouse, connected to %', current_database();
    END IF;
END;
$check$;

ALTER TYPE public.dn_type_enum ADD VALUE IF NOT EXISTS 'damage_to_supplier';
ALTER TYPE public.payment_status_enum ADD VALUE IF NOT EXISTS 'failed';
COMMIT;

SELECT current_database() AS database_name, required.type_name, required.label,
       EXISTS (
           SELECT 1
           FROM pg_catalog.pg_enum
           WHERE enumtypid = to_regtype(required.type_name) AND enumlabel = required.label
       ) AS ready
FROM (VALUES
    ('public.dn_type_enum', 'damage_to_supplier'),
    ('public.payment_status_enum', 'failed')
) AS required(type_name, label);
