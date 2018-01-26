from fabric.api import *
import fabric.contrib.project as project
import os

def upload():
    local('git push heroku master')

def start():
    local('heroku ps:scale wikidata=1')
    
def stop():
    local('heroku ps:scale wikidata=0')
    
def run():
    local('python bot_wikidata.py')