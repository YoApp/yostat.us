## Getting Started

* Install [pip](http://pip.readthedocs.org/en/latest/installing.html) package manager if you haven't yet:

Linux: sudo apt-get install python-pip
Mac: brew install python

* Install [virtualenv](http://virtualenv.readthedocs.org/en/latest/virtualenv.html#installation):

sudo pip install virtualenv

* Clone this repo: 

git clone git@github.com:YoApp/yostat.us.git
cd yostat.us

* Create a virtualenv, enter it and install dependencies:

virtualenv env
. env/bin/activate
pip install -r requirements.txt

* Run the [Flask](http://flask.pocoo.org/) server to accept incoming requests on port 5000:

python server.py

* It's live: http://0.0.0.0:5000/yoteam/


![alt tag](http://cl.ly/371T26230A0d/Screen%20Shot%202016-01-15%20at%201.51.05%20PM.png)
