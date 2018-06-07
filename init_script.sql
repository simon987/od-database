PRAGMA journal_mode=WAL;

CREATE TABLE Website (

  id INTEGER PRIMARY KEY NOT NULL,
  url TEXT,
  logged_ip TEXT,
  logged_useragent TEXT,
  last_modified INTEGER DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE WebsitePath (

  id INTEGER PRIMARY KEY NOT NULL,
  website_id INTEGER,
  path TEXT,

  FOREIGN KEY (website_id) REFERENCES Website(id)
);

CREATE TABLE FileType (
  id INTEGER PRIMARY KEY NOT NULL,
  mime TEXT
);

CREATE TABLE File (
  id INTEGER PRIMARY KEY NOT NULL,
  path_id INTEGER,
  mime_id INTEGER,
  name TEXT,
  size INTEGER,

  FOREIGN KEY (path_id) REFERENCES WebsitePath(id),
  FOREIGN KEY (mime_id) REFERENCES FileType(id)
);

CREATE TABLE Queue (
  id INTEGER PRIMARY KEY NOT NULL,
  website_id INTEGER UNIQUE,
  reddit_post_id TEXT,
  reddit_comment_id TEXT,
  priority INTEGER
);

-- Full Text Index

CREATE VIRTUAL TABLE File_index USING fts5 (
  name,
  path,
  tokenize=porter
);

CREATE TRIGGER after_File_index_insert AFTER INSERT ON File BEGIN

  INSERT INTO File_index (rowid, name, path)
    SELECT File.id, File.name, WebsitePath.path
      FROM File
      INNER JOIN WebsitePath on File.path_id = WebsitePath.id
      WHERE File.id = new.id;
END;

CREATE TRIGGER after_File_index_delete AFTER DELETE ON File BEGIN
  DELETE FROM File_index WHERE rowid = old.id;
END;