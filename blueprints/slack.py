from core import redis_store
import os
import urllib
from flask import Blueprint, request, render_template, redirect, session
import requests

slack_bp = Blueprint('slack_bp', __name__, template_folder='templates')


@slack_bp.route('/slack/')
def slack():
    if request.args.get('code'):
        response = requests.post('https://slack.com/api/oauth.access', data={
            'client_id': os.environ.get('SLACK_CLIENT_ID'),
            'client_secret': os.environ.get('SLACK_CLIENT_SECRET'),
            'code': request.args.get('code')
        })
        json_response = response.json()
        if json_response.get('access_token'):
            response = requests.post('https://slack.com/api/auth.test', data={
                'token': json_response.get('access_token')
            })
            json_response = response.json()
            slack_user_id = json_response.get('user_id')
            session['slack_user_id'] = slack_user_id

            url = 'https://dashboard.justyo.co/authorize/?'
            params = {
                'client_id': os.environ.get('YO_CLIENT_ID'),
                'response_type': 'code',
                'redirect_uri': os.environ.get('YO_REDIRECT_URI'),
                'scope': 'basic',
            }
            return redirect(url + urllib.urlencode(params))

    return render_template('slack.html')



@slack_bp.route('/authorized/')
def authorized():
    print request.args
    if request.args.get('code'):
        response = requests.post('https://dashboard.justyo.co/token/', data={
            'code': request.args.get('code'),
            'client_id': os.environ.get('YO_CLIENT_ID'),
            'client_secret': os.environ.get('YO_CLIENT_SECRET'),
            'redirect_uri': os.environ.get('YO_REDIRECT_URI'),
            'grant_type': 'authorization_code'
        })
        json_response = response.json()
        if json_response.get('access_token'):
            yo_token = json_response.get('access_token')
            response = requests.get('https://api.justyo.co/me/?access_token=' + yo_token)
            json_response = response.json()
            username = json_response.get('username')
            if username:

                session['access_token'] = yo_token
                session['username'] = username
                session['display_name'] = json_response.get('display_name')

                slack_user_id = session.get('slack_user_id')
                if slack_user_id:
                    redis_store.set(slack_user_id, yo_token)
                    del session['slack_user_id']
                    return render_template('slack.html', done=True)

    return redirect('/?add=1')


@slack_bp.route('/set/', methods=['POST'])
def set_status():
    slack_user_id = request.form.get('user_id')
    text = request.form.get('text')
    yo_access_token = redis_store.get(slack_user_id)
    response = requests.post('https://api.justyo.co/status/', json={
        'status': text,
        'access_token': yo_access_token
    })
    if response.status_code == 200:
        response = requests.get('https://api.justyo.co/me/?access_token=' + yo_access_token)
        json_response = response.json()
        return 'Your Yo Status is now: ' + text + ' (yostat.us/' + json_response.get('username') + ')'
    else:
        return 'Couldn\'t set your Yo Status :('
