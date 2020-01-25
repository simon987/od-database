from flask import Flask

import api
import common
import config
import template_filters
import views
import os

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET
template_filters.setup_template_filters(app)

views.setup_views(app)
api.setup_api(app)


if os.environ.get("ODDB_USER", False) and os.environ.get("ODDB_PASSWORD", False):
    user = os.environ["ODDB_USER"]
    password = os.environ["ODDB_PASSWORD"]
    common.db.generate_login(user, password)
    print("Generated user %s" % user)

if __name__ == '__main__':
    app.run("0.0.0.0", port=80, threaded=True)
