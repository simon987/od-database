import datetime
import time

import od_util


def setup_template_filters(app):

    app.jinja_env.globals.update(truncate_path=od_util.truncate_path)
    app.jinja_env.globals.update(get_color=od_util.get_color)
    app.jinja_env.globals.update(get_mime=od_util.get_category)

    @app.template_filter("date_format")
    def date_format(value, format='%Y-%m-%d'):
        return time.strftime(format, time.gmtime(value))

    @app.template_filter("datetime_format")
    def datetime_format(value, format='%Y-%m-%d %H:%M:%S'):
        return time.strftime(format, time.gmtime(value))

    @app.template_filter("duration_format")
    def duration_format(value):
        delay = datetime.timedelta(seconds=value)
        if delay.days > 0:
            out = str(delay).replace(" days, ", ":")
        else:
            out = str(delay)
        out_ar = out.split(':')
        out_ar = ["%02d" % (int(float(x))) for x in out_ar]
        out = ":".join(out_ar)
        return out

    @app.template_filter("from_timestamp")
    def from_timestamp(value):
        return datetime.datetime.fromtimestamp(value)
