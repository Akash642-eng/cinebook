BEGIN;

ALTER TABLE bookings
    ALTER COLUMN status SET DEFAULT 'pending_payment';

ALTER TABLE bookings
    DROP CONSTRAINT ck_booking_status_valid;

ALTER TABLE bookings
    ADD CONSTRAINT ck_booking_status_valid
    CHECK (status IN ('pending_payment', 'confirmed', 'cancelled'));

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    booking_id INTEGER NOT NULL
        REFERENCES bookings(id) ON DELETE RESTRICT,
    amount_paise INTEGER NOT NULL
        CONSTRAINT ck_payment_amount_positive CHECK (amount_paise > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    provider VARCHAR(20) NOT NULL DEFAULT 'sandbox'
        CONSTRAINT ck_payment_provider_sandbox CHECK (provider = 'sandbox'),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CONSTRAINT ck_payment_status_valid CHECK (status IN ('pending', 'succeeded', 'failed')),
    reference VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_payments_booking_id ON payments (booking_id);

COMMIT;
