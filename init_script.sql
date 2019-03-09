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
