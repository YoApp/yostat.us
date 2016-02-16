from core import redis_store
from flask.ext.cors import CORS
import os
from flask import Flask
from blueprints.site import site_bp
from blueprints.slack import slack_bp
from blueprints.twitter import twitter_bp, start_stream_listener


app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config.update(
    DEBUG=True,
    SECRET_KEY=os.environ.get('SECRET_KEY'),
    REDIS_URL=os.environ.get('REDISCLOUD_URL')
)

app.register_blueprint(slack_bp)
app.register_blueprint(site_bp)
app.register_blueprint(twitter_bp)

start_stream_listener()


if __name__ == "__main__":
    port = os.environ.get("PORT", "5000")
    redis_store.init_app(app)
    app.run(host="0.0.0.0", port=int(port), use_reloader=False)