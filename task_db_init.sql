
CREATE TABLE Queue (
  id INTEGER PRIMARY KEY,
  url TEXT,
  priority INTEGER,
  callback_type TEXT,
  callback_args TEXT
);