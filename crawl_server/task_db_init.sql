
CREATE TABLE Queue (
  id INTEGER PRIMARY KEY,
  website_id INTEGER,
  url TEXT,
  priority INTEGER,
  callback_type TEXT,
  callback_args TEXT
);

CREATE TABLE TaskResult (
  id INTEGER PRIMARY KEY,
  website_id INT,
  status_code TEXT,
  file_count INT,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  indexed_time TIMESTAMP DEFAULT NULL
);