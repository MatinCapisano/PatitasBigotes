-- Add support for cash change ("vuelto") in payments.
-- PostgreSQL:
ALTER TABLE payments
ADD COLUMN IF NOT EXISTS change_amount INTEGER;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ck_payments_change_amount_non_negative'
  ) THEN
    ALTER TABLE payments
    ADD CONSTRAINT ck_payments_change_amount_non_negative
    CHECK (change_amount IS NULL OR change_amount >= 0);
  END IF;
END
$$;

-- SQLite fallback (manual):
-- 1) ALTER TABLE payments ADD COLUMN change_amount INTEGER;
-- 2) Optional integrity guard should be enforced at app-level validation.
