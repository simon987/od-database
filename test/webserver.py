from flask import Flask, send_file

app = Flask(__name__)


@app.route("/test1/")
def test1():
    return send_file("files/apache_table.html")


if __name__ == '__main__':
    app.run("0.0.0.0", port=8888, threaded=True)

