ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_sent_at TIMESTAMP;

CREATE TABLE IF NOT EXISTS auth_action_tokens (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  action VARCHAR NOT NULL,
  token_hash VARCHAR NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  used_at TIMESTAMP NULL,
  requested_ip VARCHAR NULL,
  meta TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_auth_action_tokens_token_hash
  ON auth_action_tokens(token_hash);
CREATE INDEX IF NOT EXISTS ix_auth_action_tokens_user_action_expires
  ON auth_action_tokens(user_id, action, expires_at);
CREATE INDEX IF NOT EXISTS ix_auth_action_tokens_action_expires
  ON auth_action_tokens(action, expires_at);
CREATE INDEX IF NOT EXISTS ix_auth_action_tokens_used_at
  ON auth_action_tokens(used_at);
