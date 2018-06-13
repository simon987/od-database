from app import app
import config
import ssl

if __name__ == '__main__':
    if not config.USE_SSL:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.load_cert_chain('certificates/cert.pem', 'certificates/privkey.pem')
        app.run("0.0.0.0", port=12345, ssl_context=context, threaded=True)
    else:
        app.run("0.0.0.0", port=12345, threaded=True)
