SELECT Website.url, WebsitePath.path, File.name, File.size, MT.mime
  FROM File
    INNER JOIN WebsitePath on File.path_id = WebsitePath.id
    INNER JOIN Website on WebsitePath.website_id = Website.id
    INNER JOIN FileType MT on File.mime_id = MT.id;
