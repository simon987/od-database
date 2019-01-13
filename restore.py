from search.search import ElasticSearchEngine
import ujson

es = ElasticSearchEngine("od-database")
es.reset()

with open("dump.json", "r") as f:

    buffer = list()
    index_every = 10000

    for line in f:
        try:
            doc = ujson.loads(line)["_source"]
            buffer.append(doc)

            if len(buffer) >= index_every:
                es._index(buffer)
                buffer.clear()

        except Exception as e:
            print("ERROR: " + str(e))

    es._index(buffer)

