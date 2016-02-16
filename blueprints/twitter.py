# -*- coding: utf-8 -*-
import urllib
from core import redis_store
from flask import request, Blueprint, session, redirect, render_template
import flask
import requests
import tweepy
import os
import emoji


# Twitter client with read only permissions because we don't need to tweet on behalf of users
USER_TWITTER_CONSUMER_TOKEN = os.environ.get('USER_TWITTER_CONSUMER_TOKEN')
USER_TWITTER_CONSUMER_SECRET = os.environ.get('USER_TWITTER_CONSUMER_SECRET')
USER_TWITTER_CALLBACK_URL = os.environ.get('USER_TWITTER_CALLBACK_URL')


# Twitter client with read/write permissions to allow tweeting back results
APP_TWITTER_CONSUMER_TOKEN = os.environ.get('APP_TWITTER_CONSUMER_TOKEN')
APP_TWITTER_CONSUMER_SECRET = os.environ.get('APP_TWITTER_CONSUMER_SECRET')
APP_TWITTER_CALLBACK_URL = os.environ.get('APP_TWITTER_CALLBACK_URL')
APP_TWITTER_OAUTH_TOKEN = os.environ.get('APP_TWITTER_OAUTH_TOKEN')
APP_TWITTER_OAUTH_SECRET = os.environ.get('APP_TWITTER_OAUTH_SECRET')


# YOAuth client credentials
YO_STATUS_TWITTER_CLIENT_ID = os.environ.get('YO_STATUS_TWITTER_CLIENT_ID')
YO_STATUS_TWITTER_CLIENT_SECRET = os.environ.get('YO_STATUS_TWITTER_CLIENT_SECRET')
YO_STATUS_TWITTER_REDIRECT_URI = os.environ.get('YO_STATUS_TWITTER_REDIRECT_URI')


app_auth = tweepy.OAuthHandler(APP_TWITTER_CONSUMER_TOKEN,
                               APP_TWITTER_CONSUMER_SECRET,
                               APP_TWITTER_CALLBACK_URL)

app_auth.set_access_token(APP_TWITTER_OAUTH_TOKEN,
                          APP_TWITTER_OAUTH_SECRET)

app_api = tweepy.API(app_auth)


twitter_bp = Blueprint('twitter_bp', __name__, template_folder='templates')


@twitter_bp.route("/twitter")
@twitter_bp.route("/twitter/")
def twitter():
    twitter_user_id = session['twitter_user_id']
    if twitter_user_id:
        status_url = 'https://yostat.us/' + session['yo_username']
        return render_template('twitter.html', status_url=status_url, done=True)
    else:
        return authorize()


@twitter_bp.route("/twitter/authorize")
def authorize():
    try:
        user_auth = tweepy.OAuthHandler(USER_TWITTER_CONSUMER_TOKEN,
                                        USER_TWITTER_CONSUMER_SECRET,
                                        USER_TWITTER_CALLBACK_URL)
        redirect_url = user_auth.get_authorization_url()
    except tweepy.TweepError as e:
        print 'Error! Failed to get request token'
        redirect_url = 'http://yostat.us'

    return flask.redirect(redirect_url)


@twitter_bp.route("/twitter/authorized")
def authorized():

    verifier = request.args['oauth_verifier']
    try:
        user_auth = tweepy.OAuthHandler(USER_TWITTER_CONSUMER_TOKEN,
                                        USER_TWITTER_CONSUMER_SECRET,
                                        USER_TWITTER_CALLBACK_URL)
        user_auth.request_token = {'oauth_token': request.args.get('oauth_token'),
                                   'oauth_token_secret': request.args.get('oauth_verifier')}
        user_auth.get_access_token(verifier)
    except tweepy.TweepError as e:
        print 'Error! Failed to get access token: ' + str(e.message)
        redirect_url = 'http://yostat.us'
        return redirect(redirect_url)

    api = tweepy.API(user_auth)
    twitter_user_id = api.me().id

    session['twitter_user_id'] = str(twitter_user_id)

    url = 'https://dashboard.justyo.co/authorize/?'
    params = {
        'client_id': YO_STATUS_TWITTER_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': YO_STATUS_TWITTER_REDIRECT_URI,
        'scope': 'basic'
    }
    return redirect(url + urllib.urlencode(params))


@twitter_bp.route('/twitter/authorized/yo/')
def authorized_yo():
    print request.args
    if request.args.get('code') and request.args.get('state'):
        response = requests.post('https://dashboard.justyo.co/token/', data={
            'code': request.args.get('code'),
            'client_id': YO_STATUS_TWITTER_CLIENT_ID,
            'client_secret': YO_STATUS_TWITTER_CLIENT_SECRET,
            'redirect_uri': YO_STATUS_TWITTER_REDIRECT_URI,
            'grant_type': 'authorization_code'
        })
        json_response = response.json()
        if json_response.get('access_token'):
            yo_token = json_response.get('access_token')
            response = requests.get('https://api.justyo.co/me/?access_token=' + yo_token)
            json_response = response.json()
            username = json_response.get('username')
            if username:
                session['yo_username'] = username
                redis_store.set('yo.token.for.twitter.user.id:' + session['twitter_user_id'], yo_token)
                status_url = 'https://yostat.us/' + session['yo_username']
                return render_template('twitter.html', status_url=status_url, done=True)

    return render_template('twitter.html')


class MyStreamListener(tweepy.StreamListener):

    def on_status(self, tweet):
        try:
            twitter_user_id = str(tweet.user.id)
            splitted = tweet.text.split(' ')
            if len(splitted) <= 3:

                emoji_status = splitted[1]
                is_valid_emoji = emoji.demojize(emoji_status) != emoji_status

                if not is_valid_emoji:
                    app_api.update_status(status=u'@' + tweet.user.screen_name + u' try again with a single emoji: ".YoApp 😂"')
                    return

                yo_access_token = redis_store.get('yo.token.for.twitter.user.id:' + twitter_user_id)
                if not yo_access_token:
                    app_api.update_status(status=u'@' + tweet.user.screen_name + u' let\'s link your twitter to your Yo Status here: https://yostat.us/twitter/authorize')
                    return

                response = requests.post('https://api.justyo.co/status/', json={
                    'status': emoji_status,
                    'access_token': yo_access_token
                })

                if response.status_code == 200:
                    app_api.update_status(status=u'@' + tweet.user.screen_name + u' your status is now: ' + emoji)
                else:
                    app_api.update_status(status=u'@' + tweet.user.screen_name + u' let\'s link your twitter to your Yo Status here: https://yostat.us/twitter/authorize')
        except Exception as e:
            print e.message


def start_stream_listener():
    listener = MyStreamListener()
    #api = tweepy.API(app_auth)
    #twitter_user_id = api.me().id
    stream = tweepy.Stream(auth=app_auth, listener=listener)
    stream.filter(track=['@YoApp'], async=True)


