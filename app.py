from flask import Flask

import api
import config
import template_filters
import views

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET
template_filters.setup_template_filters(app)


views.setup_views(app)
api.setup_api(app)

if __name__ == '__main__':
    app.run("0.0.0.0", port=12345, threaded=True)
