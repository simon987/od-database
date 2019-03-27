DROP TABLE IF EXISTS Website, Admin, BlacklistedWebsite, ApiClient, SearchLogEntry;

CREATE TABLE Website (

  id SERIAL PRIMARY KEY NOT NULL,
  url TEXT,
  logged_ip TEXT,
  logged_useragent TEXT,
  last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Admin (
  username TEXT PRIMARY KEY NOT NULL,
  password BYTEA,
  role TEXT
);

CREATE TABLE BlacklistedWebsite (
  id SERIAL PRIMARY KEY NOT NULL,
  url TEXT
);

CREATE TABLE ApiClient (
  name TEXT PRIMARY KEY NOT NULL,
  token TEXT NOT NULL
);

CREATE TABLE SearchLogEntry (
  id SERIAL PRIMARY KEY,
  search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  remote_addr TEXT,
  forwarded_for TEXT,
  query TEXT,
  extensions TEXT,
  page INT,
  blocked BOOLEAN DEFAULT FALSE,
  results INT DEFAULT 0,
  took INT DEFAULT 0
);
