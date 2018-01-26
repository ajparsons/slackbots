'''
Created on 25 Jan 2018

@author: Alex
'''
import re
import os
import requests
import json
import string
import sys
import time
from slackclient import SlackClient

# instantiate Slack client
slack_bot_token = os.environ.get("BOT_WIKIDATA",None)

if slack_bot_token == None:
    print "no token in BOT_WIKIDATA"
    sys.exit()
    
slack_client = SlackClient(slack_bot_token)
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "do"

def no_pun(v):
    exclude = set(string.punctuation)
    s = ''.join(ch for ch in v if ch not in exclude)
    return s

def get_entry(q):
    q = q.upper()
    url = "https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=labels&ids={0}".format(q)
    content = requests.get(url).content
    j = json.loads(content)["entities"]
    if q in j:
        labels = j[q]["labels"]
        english = labels["en"]
        return english["value"]
    return None

def make_message(groups,message):
    words = set(no_pun(message.lower()).split(" "))
    lines = []
    q_url_format = "<https://www.wikidata.org/wiki/{0}|{0}>"
    p_url_format = "<https://www.wikidata.org/wiki/Property:{0}|{0}>"
    print groups
    for g in groups:
        g = g.upper()
        try:
            label = get_entry(g)
            label_bits = set(no_pun(label.lower()).split(" "))
        except Exception:
            label = "No English Label"
            label_bits = set([])
        if g[0] == "P":
            url_formatted = p_url_format.format(g)
        else:
            url_formatted = q_url_format.format(g)
        line = u"{0}: {1}".format(url_formatted,label)
        if len(label_bits.intersection(words)) == 0:
            lines.append(line)
    return "\n\r".join(lines)
    

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            matches = get_wikidata_items(event["text"])
            #print matches
            if matches:
                message = make_message(matches,event["text"])
                return message, event["channel"]
            #if user_id == starterbot_id:
            #    return message, event["channel"]
    return None, None

def get_wikidata_items(message_text):

    MENTION_REGEX = "([QPqp]\d+)"
    
    matches = re.findall(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    
    if matches:
        return matches
    else:
        return []

def handle_command(command, channel):
    """
        Executes bot command if the command is known
    """

    # Finds and executes the given command, filling in response
    response = command

    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response
    )
    
def bot_loop():
    if slack_client.rtm_connect():
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
    
if __name__ == "__main__":
    #print get_wikidata_items("This is a test of a message mention a Q10769147 or a P101 that also contains qwords and persons.")
    bot_loop()
    #print get_entry("Q10769147")