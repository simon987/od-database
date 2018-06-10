from scrapy import Item, Field


class File(Item):
    path = Field()
    name = Field()
    mime = Field()
    mtime = Field()
    size = Field()
