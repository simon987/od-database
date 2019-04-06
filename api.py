import json
from uuid import uuid4

from flask import request, abort, send_file, session

import captcha
import common as oddb
from common import taskManager
from database import Website
from search.search import InvalidQueryException


def setup_api(app):
    taskManager.start_indexer_threads()

    @app.route("/api/website/by_url", methods=["GET"])
    def api_website_by_url():
        token = request.args.get("token")
        name = oddb.db.check_api_token(token)

        if name:
            url = request.args.get("url")
            website = oddb.db.get_website_by_url(url)
            oddb.logger.info("API get website by url '" + url + "' by " + name)
            if website:
                return str(website.id)
            return abort(404)
        else:
            return abort(403)

    @app.route("/api/website/blacklisted", methods=["GET"])
    def api_website_is_blacklisted():
        token = request.args.get("token")
        url = request.args.get("url")
        name = oddb.db.check_api_token(token)

        if name:
            oddb.logger.info("API get website is blacklisted '" + url + "' by " + name)
            return str(oddb.db.is_blacklisted(url))
        else:
            return abort(403)

    @app.route("/api/website/add", methods=["GET"])
    def api_add_website():
        token = request.args.get("token")
        url = request.args.get("url")

        name = oddb.db.check_api_token(token)
        if name:

            website_id = oddb.db.insert_website(Website(url, str(request.remote_addr + "_" +
                                                                 request.headers.get("X-Forwarded-For", "")),
                                                        "API_CLIENT_" + name))
            oddb.logger.info("API add website '" + url + "' by " + name + "(" + str(website_id) + ")")
            return str(website_id)
        else:
            return abort(403)

    @app.route("/api/website/random")
    def api_random_website():
        token = request.json["token"]
        name = oddb.db.check_api_token(token)

        if name:
            oddb.logger.info("API get random website by " + name)
            return str(oddb.db.get_random_website_id())
        else:
            return abort(403)

    @app.route("/api/search", methods=["POST"])
    def api_search():
        token = request.json["token"]
        name = oddb.db.check_api_token(token)

        if name:

            try:
                hits = oddb.searchEngine.search(
                    request.json["query"],
                    request.json["page"], request.json["per_page"],
                    request.json["sort_order"],
                    request.json["extensions"],
                    request.json["size_min"], request.json["size_max"],
                    request.json["match_all"],
                    request.json["fields"],
                    request.json["date_min"], request.json["date_max"]
                )

                hits = oddb.db.join_website_on_search_result(hits)
                oddb.logger.info("API search '" + request.json["query"] + "' by " + name)
                return json.dumps(hits)

            except InvalidQueryException as e:
                oddb.logger.info("API search failed: " + str(e))
                return str(e)
        else:
            return abort(403)

    @app.route("/cap", methods=["GET"])
    def cap():
        word = captcha.make_captcha()
        cap_id = uuid4().__str__()
        session["cap"] = cap_id

        oddb.redis.set(cap_id, word)

        return send_file(captcha.get_path(word), cache_timeout=0)

