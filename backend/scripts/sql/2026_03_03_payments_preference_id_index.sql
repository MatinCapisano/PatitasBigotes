-- Add dedicated Mercadopago preference identifier column
ALTER TABLE payments
ADD COLUMN preference_id VARCHAR NULL;

-- Fast lookup by preference_id for webhook/payment reconciliation paths
CREATE INDEX ix_payments_preference_id ON payments(preference_id);

