-- Separate Saudi-only tables. Use on the NEW Saudi database only.
CREATE TABLE IF NOT EXISTS public.sa_tv_stocks_1d (
  symbol TEXT NOT NULL,
  session_date DATE NOT NULL,
  o DOUBLE PRECISION,
  h DOUBLE PRECISION NOT NULL,
  l DOUBLE PRECISION,
  c DOUBLE PRECISION NOT NULL,
  volume DOUBLE PRECISION,
  PRIMARY KEY(symbol, session_date),
  CHECK (c > 0), CHECK (h > 0)
);
CREATE INDEX IF NOT EXISTS sa_stocks_session_idx ON public.sa_tv_stocks_1d(session_date);
CREATE TABLE IF NOT EXISTS public.sa_tv_indices_1d (
  symbol TEXT NOT NULL,
  session_date DATE NOT NULL,
  o DOUBLE PRECISION,
  h DOUBLE PRECISION,
  l DOUBLE PRECISION,
  c DOUBLE PRECISION NOT NULL,
  volume DOUBLE PRECISION,
  PRIMARY KEY(symbol, session_date),
  CHECK (c > 0)
);
