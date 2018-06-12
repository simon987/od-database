import elasticsearch
from elasticsearch.exceptions import TransportError


class IndexingError(Exception):
    pass


class SearchEngine:

    def __init__(self):
        pass

    def import_json(self, in_file: str, website_id: int):
        raise NotImplementedError

    def search(self, query) -> {}:
        raise NotImplementedError

    def scroll(self, scroll_id) -> {}:
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def ping(self):
        raise NotImplementedError


class ElasticSearchEngine(SearchEngine):

    def __init__(self, index_name):
        super().__init__()
        self.index_name = index_name
        self.es = elasticsearch.Elasticsearch()

        if not self.es.indices.exists(self.index_name):
            self.init()

    def init(self):
        print("Elasticsearch first time setup")
        if self.es.indices.exists(self.index_name):
            self.es.indices.delete(index=self.index_name)
        self.es.indices.create(index=self.index_name)
        self.es.indices.close(index=self.index_name)

        # File names and paths
        self.es.indices.put_settings(body=
                                     {"analysis": {
                                         "tokenizer": {
                                             "my_nGram_tokenizer": {
                                                 "type": "nGram", "min_gram": 3, "max_gram": 3}
                                         }
                                     }}, index=self.index_name)
        self.es.indices.put_settings(body=
                                     {"analysis": {
                                         "analyzer": {
                                             "my_nGram": {
                                                 "tokenizer": "my_nGram_tokenizer",
                                                 "filter": ["lowercase", "asciifolding"]
                                             }
                                         }
                                     }}, index=self.index_name)

        # Mappings
        self.es.indices.put_mapping(body={"properties": {
            "path": {"analyzer": "my_nGram", "type": "text"},
            "name": {"analyzer": "my_nGram", "type": "text"},
            "mtime": {"type": "date", "format": "epoch_millis"},
            "size": {"type": "long"},
            "website_id": {"type": "integer"}
        }}, doc_type="file", index=self.index_name)

        self.es.indices.open(index=self.index_name)

    def reset(self):
        self.init()

    def ping(self):
        return self.es.ping()

    def import_json(self, in_file: str, website_id: int):
        import_every = 1000

        with open(in_file, "r") as f:
            docs = []

            line = f.readline()
            while line:
                docs.append(line[:-1])  # Remove trailing new line

                if len(docs) >= import_every:
                    self._index(docs, website_id)
                    docs.clear()
                line = f.readline()
            self._index(docs, website_id)

    def _index(self, docs, website_id):
        print("Indexing " + str(len(docs)) + " docs")
        bulk_string = ElasticSearchEngine.create_bulk_index_string(docs, website_id)
        result = self.es.bulk(body=bulk_string, index=self.index_name, doc_type="file")

        if result["errors"]:
            print(result)
            raise IndexingError

    @staticmethod
    def create_bulk_index_string(docs: list, website_id: int):

        result = ""

        action_string = '{"index":{}}\n'
        website_id_string = ',"website_id":' + str(website_id) + '}\n'  # Add website_id param to each doc

        for doc in docs:
            result += action_string + doc[:-1] + website_id_string
        return result

    def search(self, query) -> {}:

        filters = []

        page = self.es.search(body={
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": ["name", "path"],
                            "operator": "and"
                        }
                    },
                    "filter": filters
                }
            },
            "sort": [
                "_score"
            ],
            "highlight": {
                "fields": {
                    "name": {"pre_tags": ["<span class='hl'>"], "post_tags": ["</span>"]},
                }
            },
            "size": 40}, index=self.index_name, scroll="8m")

        # todo get scroll time from config
        # todo get size from config
        return page

    def scroll(self, scroll_id) -> {}:
        try:
            return self.es.scroll(scroll_id=scroll_id, scroll="3m")  # todo get scroll time from config
        except TransportError:
            return None
