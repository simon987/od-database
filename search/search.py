import elasticsearch
from elasticsearch import helpers
import os
import ujson


class IndexingError(Exception):
    pass


class SearchEngine:

    def __init__(self):
        pass

    def import_json(self, in_str: str, website_id: int):
        raise NotImplementedError

    def search(self, query, page, per_page, sort_order) -> {}:
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def ping(self):
        raise NotImplementedError

    def get_stats(self, website_id: int, subdir: str = None):
        raise NotImplementedError


class ElasticSearchEngine(SearchEngine):
    SORT_ORDERS = {
        "score": ["_score"],
        "size_asc": [{"size": {"order": "asc"}}],
        "size_dsc": [{"size": {"order": "desc"}}],
        "date_asc": [{"mtime": {"order": "asc"}}],
        "date_desc": [{"mtime": {"order": "desc"}}],
        "none": []
    }

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
        self.es.indices.put_settings(body={
            "analysis": {
                "tokenizer": {
                    "my_nGram_tokenizer": {
                        "type": "nGram", "min_gram": 3, "max_gram": 3}
                }
            }}, index=self.index_name)
        self.es.indices.put_settings(body={
            "analysis": {
                "analyzer": {
                    "my_nGram": {
                        "tokenizer": "my_nGram_tokenizer",
                        "filter": ["lowercase", "asciifolding"]
                    }
                }
            }}, index=self.index_name)

        # Mappings
        self.es.indices.put_mapping(body={"properties": {
            "path": {"analyzer": "standard", "type": "text"},
            "name": {"analyzer": "standard", "type": "text", "fields": {"nGram": {"type": "text", "analyzer": "my_nGram"}}},
            "mtime": {"type": "date", "format": "epoch_millis"},
            "size": {"type": "long"},
            "website_id": {"type": "integer"},
            "ext": {"type": "keyword"}
        }}, doc_type="file", index=self.index_name)

        self.es.indices.open(index=self.index_name)

    def reset(self):
        self.init()

    def ping(self):
        return self.es.ping()

    def import_json(self, in_lines, website_id: int):

        import_every = 5000

        docs = []

        for line in in_lines:
            doc = ujson.loads(line)
            name, ext = os.path.splitext(doc["name"])
            doc["ext"] = ext[1:].lower() if ext and len(ext) > 1 else ""
            doc["name"] = name
            doc["website_id"] = website_id
            docs.append(doc)

            if len(docs) >= import_every:
                self._index(docs)
                docs.clear()
        self._index(docs)

    def _index(self, docs):
        print("Indexing " + str(len(docs)) + " docs")
        bulk_string = ElasticSearchEngine.create_bulk_index_string(docs)
        result = self.es.bulk(body=bulk_string, index=self.index_name, doc_type="file", request_timeout=30)

        if result["errors"]:
            print(result)
            raise IndexingError

    @staticmethod
    def create_bulk_index_string(docs: list):

        action_string = '{"index":{}}\n'
        return "\n".join("".join([action_string, ujson.dumps(doc)]) for doc in docs)

    def search(self, query, page, per_page, sort_order) -> {}:

        filters = []
        sort_by = ElasticSearchEngine.SORT_ORDERS.get(sort_order, [])

        page = self.es.search(body={
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": ["name^5", "name.nGram^2", "path"],
                            "operator": "or"
                        }
                    },
                    "filter": filters
                }
            },
            "sort": sort_by,
            "highlight": {
                "fields": {
                    "name": {"pre_tags": ["<span class='hl'>"], "post_tags": ["</span>"]},
                    "path": {"pre_tags": ["<span class='hl'>"], "post_tags": ["</span>"]}
                }
            },
            "size": per_page, "from": page * per_page}, index=self.index_name)

        return page

    def get_stats(self, website_id: int, subdir: str = None):

        result = self.es.search(body={
            "query": {
                "constant_score": {
                    "filter": {
                        "term": {"website_id": website_id}
                    }
                }
            },
            "aggs": {
                "ext_group": {
                    "terms": {
                        "field": "ext"
                    },
                    "aggs": {
                        "size": {
                            "sum": {
                                "field": "size"
                            }
                        }
                    }
                },
                "total_size": {
                    "sum_bucket": {
                        "buckets_path": "ext_group>size"
                    }
                }
            },
            "size": 0
        })

        stats = dict()
        stats["total_size"] = result["aggregations"]["total_size"]["value"]
        stats["total_count"] = result["hits"]["total"]
        stats["ext_stats"] = [(b["size"]["value"], b["doc_count"], b["key"])
                              for b in result["aggregations"]["ext_group"]["buckets"]]

        return stats

    def get_link_list(self, website_id, base_url):

        hits = helpers.scan(client=self.es,
                            query={
                                "_source": {
                                    "includes": ["path", "name", "ext"]
                                },
                                "query": {
                                    "term": {
                                        "website_id": website_id}
                                }
                            },
                            index=self.index_name)
        for hit in hits:
            src = hit["_source"]
            yield base_url + src["path"] + ("/" if src["path"] != "" else "") + src["name"] + \
                  ("." if src["ext"] != "" else "") + src["ext"]

    def get_global_stats(self):

        result = self.es.search(body={
            "query": {
                "match_all": {}
            },
            "aggs": {
                "total_size": {
                    "sum": {"field": "size"}
                }
            },
            "size": 0
        }, index=self.index_name)

        stats = dict()
        stats["file_count"] = result["hits"]["total"]
        stats["file_size"] = result["aggregations"]["total_size"]["value"]

        return stats

