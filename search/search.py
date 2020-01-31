import os
import time
from urllib.parse import urljoin

import elasticsearch
import ujson
from apscheduler.schedulers.background import BackgroundScheduler
from elasticsearch import helpers

from search import logger
from search.filter import SearchFilter


class InvalidQueryException(Exception):
    pass


class IndexingError(Exception):
    pass


class ElasticSearchEngine:
    SORT_ORDERS = {
        "score": ["_score"],
        "size_asc": [{"size": {"order": "asc"}}],
        "size_dsc": [{"size": {"order": "desc"}}],
        "date_asc": [{"mtime": {"order": "asc"}}],
        "date_desc": [{"mtime": {"order": "desc"}}],
        "none": []
    }

    def __init__(self, url, index_name):
        super().__init__()
        self.index_name = index_name
        logger.info("Connecting to ES @ %s" % url)
        self.es = elasticsearch.Elasticsearch(hosts=[url])
        self.filter = SearchFilter()

        if not self.es.indices.exists(self.index_name):
            self.init()

    def start_stats_scheduler(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self._generate_global_stats, "interval", seconds=60 * 120)
        scheduler.start()

    def init(self):
        logger.info("Elasticsearch first time setup")
        if self.es.indices.exists(self.index_name):
            self.es.indices.delete(index=self.index_name)
        self.es.indices.create(index=self.index_name, body={
            "settings": {
                "index": {
                    "number_of_shards": 50,
                    "number_of_replicas": 0,
                    "refresh_interval": "30s",
                    "codec": "best_compression"
                },
                "analysis": {
                    "analyzer": {
                        "my_nGram": {
                            "tokenizer": "my_nGram_tokenizer",
                            "filter": ["lowercase", "asciifolding"]
                        }
                    },
                    "tokenizer": {
                        "my_nGram_tokenizer": {
                            "type": "nGram", "min_gram": 3, "max_gram": 3
                        }
                    }
                }
            }
        })

        # Index Mappings
        self.es.indices.put_mapping(body={
            "properties": {
                "path": {"analyzer": "standard", "type": "text"},
                "name": {"analyzer": "standard", "type": "text",
                         "fields": {"nGram": {"type": "text", "analyzer": "my_nGram"}}},
                "mtime": {"type": "date", "format": "epoch_second"},
                "size": {"type": "long"},
                "website_id": {"type": "integer"},
                "ext": {"type": "keyword"},
            },
            "_routing": {"required": True}
        }, doc_type="file", index=self.index_name, include_type_name=True)

        self.es.indices.open(index=self.index_name)

    def delete_docs(self, website_id):

        while True:
            try:
                logger.debug("Deleting docs of " + str(website_id))

                to_delete = helpers.scan(query={
                    "query": {
                        "term": {
                            "website_id": website_id
                        }
                    }
                }, scroll="1m", client=self.es, index=self.index_name, request_timeout=120, routing=website_id)

                buf = []
                counter = 0
                for doc in to_delete:
                    buf.append(doc)
                    counter += 1

                    if counter >= 10000:
                        self._delete(buf, website_id)
                        buf.clear()
                        counter = 0
                if counter > 0:
                    self._delete(buf, website_id)
                break

            except Exception as e:
                logger.error("During delete: " + str(e))
                time.sleep(10)

        logger.debug("Done deleting for " + str(website_id))

    def _delete(self, docs, website_id):
        bulk_string = self.create_bulk_delete_string(docs)
        result = self.es.bulk(body=bulk_string, index=self.index_name, doc_type="file", request_timeout=30,
                              routing=website_id)

        if result["errors"]:
            logger.error("Error in ES bulk delete: \n" + result["errors"])
            raise IndexingError

    def import_json(self, in_lines, website_id: int):

        import_every = 10000
        cooldown_time = 0

        docs = []

        for line in in_lines:
            try:
                doc = ujson.loads(line)
                name, ext = os.path.splitext(doc["name"])
                doc["ext"] = ext[1:].lower() if ext and len(ext) > 1 else ""
                doc["name"] = name
                doc["website_id"] = website_id
                docs.append(doc)
            except Exception as e:
                logger.error("Error in import_json: " + str(e) + " for line : + \n" + line)

            if len(docs) >= import_every:
                self._index(docs)
                docs.clear()
                time.sleep(cooldown_time)

        if docs:
            self._index(docs)

    def _index(self, docs):
        while True:
            try:
                logger.debug("Indexing " + str(len(docs)) + " docs")
                bulk_string = ElasticSearchEngine.create_bulk_index_string(docs)
                self.es.bulk(body=bulk_string, index=self.index_name, doc_type="file", request_timeout=30,
                             routing=docs[0]["website_id"])
                break
            except Exception as e:
                logger.error("Error in _index: " + str(e) + ", retrying")
                time.sleep(10)

    @staticmethod
    def create_bulk_index_string(docs: list):

        action_string = '{"index":{}}\n'
        return "\n".join("".join([action_string, ujson.dumps(doc)]) for doc in docs)

    @staticmethod
    def create_bulk_delete_string(docs: list):

        return "\n".join("".join(["{\"delete\":{\"_id\":\"", doc["_id"], "\"}}"]) for doc in docs)

    def search(self, query, page, per_page, sort_order, extensions, size_min, size_max, match_all, fields, date_min,
               date_max) -> {}:

        if self.filter.should_block(query):
            logger.info("Search was blocked")
            raise InvalidQueryException("One or more terms in your query is blocked by the search filter. "
                                        "This incident has been reported.")

        filters = []
        if extensions:
            filters.append({"terms": {"ext": extensions}})

        if size_min > 0 or size_max:
            size_filer = dict()
            new_filter = {"range": {"size": size_filer}}

            if size_min > 0:
                size_filer["gte"] = size_min
            if size_max:
                size_filer["lte"] = size_max

            filters.append(new_filter)

        if date_min > 0 or date_max:
            date_filer = dict()
            new_filter = {"range": {"mtime": date_filer}}

            if date_min > 0:
                date_filer["gte"] = date_min
            if date_max:
                date_filer["lte"] = date_max

            filters.append(new_filter)

        sort_by = ElasticSearchEngine.SORT_ORDERS.get(sort_order, [])

        page = self.es.search(body={
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": fields,
                            "operator": "or" if match_all else "and"
                        }
                    },
                    "filter": filters
                }
            },
            "sort": sort_by,
            "highlight": {
                "fields": {
                    "name": {"pre_tags": ["<mark>"], "post_tags": ["</mark>"]},
                    "name.nGram": {"pre_tags": ["<mark>"], "post_tags": ["</mark>"]},
                    "path": {"pre_tags": ["<mark>"], "post_tags": ["</mark>"]}
                }
            },
            "size": per_page, "from": min(page * per_page, 10000 - per_page)},
            index=self.index_name, request_timeout=20)

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
                        "field": "ext",
                        "size": 12
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
        }, index=self.index_name, request_timeout=30, routing=website_id)

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
                                    "constant_score": {
                                        "filter": {
                                            "term": {"website_id": website_id}
                                        }
                                    }
                                },
                            },
                            index=self.index_name, request_timeout=20, routing=website_id)
        for hit in hits:
            src = hit["_source"]
            yield urljoin(base_url, "/") + src["path"] + ("/" if src["path"] != "" else "") + src["name"] + \
                  ("." if src["ext"] != "" else "") + src["ext"]

    @staticmethod
    def get_global_stats():

        if os.path.exists("_stats.json"):
            with open("_stats.json", "r") as f:
                return ujson.load(f)
        else:
            return None

    def _generate_global_stats(self):

        size_per_ext = self.es.search(body={
            "query": {
                "bool": {
                    "filter": [
                        {"range": {
                            "size": {"gte": 0, "lte": (1000000000000 - 1)}  # 0-1TB
                        }}
                    ]
                }
            },
            "aggs": {
                "ext_group": {
                    "terms": {
                        "field": "ext",
                        "size": 40
                    },
                    "aggs": {
                        "size": {
                            "sum": {
                                "field": "size"
                            }
                        }
                    }
                }
            },
            "size": 0

        }, index=self.index_name, request_timeout=240)

        total_stats = self.es.search(body={
            "query": {
                "bool": {
                    "filter": [
                        {"range": {
                            "size": {"gte": 0, "lte": (1000000000000 - 1)}  # 0-1TB
                        }}
                    ]
                }
            },
            "aggs": {
                "file_stats": {
                    "extended_stats": {
                        "field": "size",
                        "sigma": 1
                    }
                }
            },
            "size": 0

        }, index=self.index_name, request_timeout=241)

        size_and_date_histogram = self.es.search(body={
            "query": {
                "bool": {
                    "filter": [
                        {"range": {
                            "size": {"gte": 0, "lte": (1000000000000 - 1)}  # 0-1TB
                        }},
                        {"range": {
                            "mtime": {
                                "gt": 0  # 1970-01-01
                            }
                        }}
                    ]
                }
            },
            "aggs": {
                "sizes": {
                    "histogram": {
                        "field": "size",
                        "interval": 100000000,  # 100Mb
                        "min_doc_count": 500
                    }
                },
                "dates": {
                    "date_histogram": {
                        "field": "mtime",
                        "interval": "1y",
                        "min_doc_count": 500,
                        "format": "yyyy"
                    }
                }
            },
            "size": 0
        }, index=self.index_name, request_timeout=242)

        website_scatter = self.es.search(body={
            "query": {
                "bool": {
                    "filter": [
                        {"range": {
                            "size": {"gte": 0, "lte": (1000000000000 - 1)}  # 0-1TB
                        }}
                    ]
                }
            },
            "aggs": {
                "websites": {
                    "terms": {
                        "field": "website_id",
                        "size": 600  # TODO: Figure out what size is appropriate
                    },
                    "aggs": {
                        "size": {
                            "sum": {
                                "field": "size"
                            }
                        }
                    }
                }
            },
            "size": 0
        }, index=self.index_name, request_timeout=243)

        es_stats = self.es.indices.stats(self.index_name, request_timeout=244)

        stats = dict()
        stats["es_index_size"] = es_stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"]
        stats["es_search_count"] = es_stats["indices"][self.index_name]["total"]["search"]["query_total"]
        stats["es_search_time"] = es_stats["indices"][self.index_name]["total"]["search"]["query_time_in_millis"]
        stats["es_search_time_avg"] = stats["es_search_time"] / (
            stats["es_search_count"] if stats["es_search_count"] != 0 else 1)

        stats["total_count"] = total_stats["aggregations"]["file_stats"]["count"]
        stats["total_size"] = total_stats["aggregations"]["file_stats"]["sum"]
        stats["size_avg"] = total_stats["aggregations"]["file_stats"]["avg"]
        stats["size_std_deviation"] = total_stats["aggregations"]["file_stats"]["std_deviation"]
        stats["size_std_deviation_bounds"] = total_stats["aggregations"]["file_stats"]["std_deviation_bounds"]
        stats["size_variance"] = total_stats["aggregations"]["file_stats"]["variance"]
        stats["ext_stats"] = [(b["size"]["value"], b["doc_count"], b["key"])
                              for b in size_per_ext["aggregations"]["ext_group"]["buckets"]]
        stats["sizes_histogram"] = [(b["key"], b["doc_count"])
                                    for b in size_and_date_histogram["aggregations"]["sizes"]["buckets"]]
        stats["dates_histogram"] = [(b["key_as_string"], b["doc_count"])
                                    for b in size_and_date_histogram["aggregations"]["dates"]["buckets"]]
        stats["website_scatter"] = [[b["key"], b["doc_count"], b["size"]["value"]]
                                    for b in website_scatter["aggregations"]["websites"]["buckets"]]
        stats["base_url"] = "entire database"

        with open("_stats.json", "w") as f:
            ujson.dump(stats, f)

    def stream_all_docs(self):
        return helpers.scan(query={
            "query": {
                "match_all": {}
            }
        }, scroll="30s", client=self.es, index=self.index_name, request_timeout=30)

    def refresh(self):
        self.es.indices.refresh(self.index_name)
