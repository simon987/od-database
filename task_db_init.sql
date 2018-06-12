
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
  start_time INT,
  end_time INT,
  indexed_time INT DEFAULT NULL
);