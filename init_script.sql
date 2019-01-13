PRAGMA journal_mode=WAL;

CREATE TABLE Website (

  id INTEGER PRIMARY KEY NOT NULL,
  url TEXT,
  logged_ip TEXT,
  logged_useragent TEXT,
  last_modified INTEGER DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Admin (
  username TEXT PRIMARY KEY NOT NULL,
  password TEXT,
  role TEXT
);

CREATE TABLE BlacklistedWebsite (
  id INTEGER PRIMARY KEY NOT NULL,
  url TEXT
);

CREATE TABLE TaskResult (
  id INTEGER PRIMARY KEY,
  server TEXT,
  website_id INT,
  status_code TEXT,
  file_count INT,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  indexed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (server) REFERENCES ApiClient(name)
);

CREATE TABLE ApiClient (
  name TEXT PRIMARY KEY NOT NULL,
  token TEXT NOT NULL
);


CREATE TABLE SearchLogEntry (
  id INTEGER PRIMARY KEY,
  search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  remote_addr TEXT,
  forwarded_for TEXT,
  query TEXT,
  extensions TEXT,
  page INT,
  blocked INT DEFAULT 0,
  results INT DEFAULT 0,
  took INT DEFAULT 0
);

CREATE TABLE Queue (
  id INTEGER PRIMARY KEY,
  website_id INTEGER,
  url TEXT,
  priority INTEGER,
  callback_type TEXT,
  callback_args TEXT,
  assigned_crawler TEXT NULL DEFAULT NULL,

  FOREIGN KEY (assigned_crawler) REFERENCES ApiClient(name)
);
