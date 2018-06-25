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
  password TEXT
);

CREATE TABLE ApiToken (
  token TEXT PRIMARY KEY NOT NULL,
  description TEXT
);

CREATE TABLE BlacklistedWebsite (
  id INTEGER PRIMARY KEY NOT NULL,
  url TEXT
);

CREATE TABLE CrawlServer (
  id INTEGER PRIMARY KEY NOT NULL,
  url TEXT,
  name TEXT,
  token TEXT,
  slots INTEGER
);

CREATE TABLE TaskResult (
  id INTEGER PRIMARY KEY,
  server INT,
  website_id INT,
  status_code TEXT,
  file_count INT,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  indexed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (server) REFERENCES CrawlServer(id)
);
