# -*- coding: utf-8 -*-
import hashlib
import json
import urllib
from core import redis_store
from emoji import EMOJI_ALIAS_UNICODE
from flask.ext.cors import cross_origin
import os
from flask import Blueprint, render_template, request, send_from_directory, redirect, session, url_for
import requests
from user_agents import parse


site_bp = Blueprint('site_bp', __name__, template_folder='templates')


def get_user_platform():
    user_agent = request.user_agent.string.lower()
    if 'iphone' in user_agent or 'ipad' in user_agent:
        platform = 'ios'
    elif 'android' in user_agent:
        platform = 'android'
    else:
        platform = 'web'
    return platform


def emoji_to_png_url(emoji):
    try:
        index = str(repr(emoji)[4:-1]).lstrip('0').lower()
        image_url = 'http://cdn.yostat.us/emoji/' + index + '.png'
        return image_url
    except:
        return url_for('static', filename='img/favicon.png')


def add_to_wall():
    username = session['username']
    hash_object = hashlib.sha1('@' + username.lower())
    hex_dig = hash_object.hexdigest()

    should_show_banner = False

    status_url = 'https://api.justyo.co/status/sha1/u/' + hex_dig
    response = requests.get(status_url)
    if response.status_code == 404:
        requests.post('https://api.justyo.co/status',
                      json={
                          'access_token': session.get('access_token'),
                          'status': u'😂'
                      })
        should_show_banner = True

    user = {
        'display_name': session['display_name'],
        'sha1_username': hex_dig
    }

    wall_users = redis_store.lrange('wall_users', 0, 999) or []
    wall_users = map(lambda s: json.loads(s), wall_users)
    if user not in wall_users:
        redis_store.rpush('wall_users', json.dumps(user))

    session['in_wall'] = True

    return should_show_banner


@site_bp.route('/team/<usernames>')
@site_bp.route('/team/<usernames>/')
@site_bp.route('/squad/<usernames>/')
@site_bp.route('/crew/<usernames>/')
@site_bp.route('/family/<usernames>/')
@site_bp.route('/fam/<usernames>/')
def get_status_for_team(usernames):
    response = requests.get('https://api.justyo.co/status/' + usernames)
    if response.status_code == 200:
        json_object = response.json()
        results = json_object.get('results')
        if results:
            for result in results:
                status = result.get('status')
                image_url = emoji_to_png_url(status)
                result['image_url'] = image_url

            return render_template('team.html',
                                   url=request.url,
                                   results=results,
                                   image_url=image_url,
                                   sc_project=os.environ.get('sc_project'),
                                   sc_security=os.environ.get('sc_security'))

    return render_template('base.html',
                           sc_project=os.environ.get('sc_project'),
                           sc_security=os.environ.get('sc_security'))


def render_status_request(api_response):

    platform = get_user_platform()

    if api_response.status_code == 200:
        json_object = api_response.json()
        status = json_object.get('status')
        if status:
            image_url = emoji_to_png_url(status)
            if request.args.get('format') == 'png':
                return redirect(image_url)

            if json_object.get('username'):
                username_lower = json_object.get('username').lower()
            else:
                username_lower = None

            return render_template('status.html',
                                   user=json_object,
                                   username_lower=username_lower,
                                   url=request.url,
                                   image_url=image_url,
                                   platform=platform,
                                   sc_project=os.environ.get('sc_project'),
                                   sc_security=os.environ.get('sc_security'))

    return render_template('base.html',
                           platform=platform,
                           sc_project=os.environ.get('sc_project'),
                           sc_security=os.environ.get('sc_security'))


@site_bp.route('/sha1/u/<sha1_username>')
@site_bp.route('/sha1/u/<sha1_username>/')
def get_sha1_username_status(sha1_username):

    api_response = requests.get('https://api.justyo.co/status/sha1/u/' + sha1_username)
    return render_status_request(api_response)



@site_bp.route('/<username>')
@site_bp.route('/<username>/')
@site_bp.route('/user/<username>')
@site_bp.route('/user/<username>/')
def get_status(username):

    api_response = requests.get('https://api.justyo.co/status/' + username)
    return render_status_request(api_response)


@site_bp.route('/')
@cross_origin()
def home():

    if request.args.get('add') and session.get('username'):
        if add_to_wall():
            pass  # present download banner

    wall_users = redis_store.lrange('wall_users', 0, 999) or []
    wall_users = map(lambda s: json.loads(s), wall_users)

    platform = get_user_platform()

    return render_template('wall.html',
                           platform=platform,
                           in_wall=session.get('in_wall', False),
                           results=wall_users,
                           sc_project=os.environ.get('sc_project'),
                           sc_security=os.environ.get('sc_security'))


@site_bp.route('/deletefromwall/', methods=['POST'])
def deletefromwall():

    username = session['username']
    hash_object = hashlib.sha1('@' + username.lower())
    hex_dig = hash_object.hexdigest()

    user = {
        'display_name': session['display_name'],
        'sha1_username': hex_dig
    }

    redis_store.lrem('wall_users', json.dumps(user))

    del session['in_wall']

    return redirect('/')


@site_bp.route('/addtowall/', methods=['POST'])
def addtowall():

    if session.get('username'):

        if add_to_wall():
            pass  # present download banner

        return redirect('/')

    else:

        url = 'https://dashboard.justyo.co/authorize/?'
        params = {
            'client_id': os.environ.get('YO_CLIENT_ID'),
            'response_type': 'code',
            'redirect_uri': os.environ.get('YO_REDIRECT_URI'),
            'scope': 'basic',
        }
        return redirect(url + urllib.urlencode(params))


@site_bp.route('/apple-app-site-association')
def apple():
    response = send_from_directory('static', 'apple-app-site-association',
                                   mimetype='application/octet-stream')
    response.headers['Content-type'] = 'application/json'
    return response


@site_bp.route('/shortnames/', methods=['GET'])
def shortnames():
    arr = sorted(EMOJI_ALIAS_UNICODE.items())
    return render_template('shortnames.html', entries=sorted(EMOJI_ALIAS_UNICODE.items()))