'''
#wikidatahelper slackbot

When people say a wikidata ID but don't explain it, this bot will!

'''
import re
import os
import requests
import json
import string
import sys
import calendar
import time
from slackclient import SlackClient

# key in enviromental variable
slack_bot_token = os.environ.get("BOT_WIKIDATA",None)

if slack_bot_token == None:
    print "no token in BOT_WIKIDATA"
    sys.exit()
    
slack_client = SlackClient(slack_bot_token)
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None
previous_store = {}

# constants
NO_REPEAT = 120 # will not repeat same help
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
def no_pun(v):
    """
    removes puntuation
    """
    exclude = set(string.punctuation)
    s = ''.join(ch for ch in v if ch not in exclude)
    return s

def get_entry(q):
    """
    get label for entry via wikidata api
    """
    q = q.upper()
    url_format = "https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=labels&ids={0}"
    url = url_format.format(q)
    content = requests.get(url).content
    j = json.loads(content)["entities"]
    if q in j:
        labels = j[q]["labels"]
        english = labels["en"]
        return english["value"]
    return None

def make_message(groups,message):
    """
    creates an explantory label for an item IF part of the label isn't already included
    in the next
    """
    words = set(no_pun(message.lower()).split(" "))
    lines = []
    q_url_format = "<https://www.wikidata.org/wiki/{0}|{0}>"
    p_url_format = "<https://www.wikidata.org/wiki/Property:{0}|{0}>"
    
    unique = []
    [unique.append(item) for item in groups if item not in unique]
    print groups
    for g in unique:
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
        #if none of the words have been used
        if len(label_bits.intersection(words)) == 0:
            lines.append(line)
    return "\n\r".join(lines)
    
def remove_recent(matches,timestamp):
    """
    has a cool down before it repeats what a property was
    """
    global previous_store
    now = calendar.timegm(time.gmtime())
    final = []
    for m in matches:
        previous = previous_store.get(m,None)
        if previous:
            distance = now - previous
            if distance > NO_REPEAT:
                final.append(m)
        else:
            final.append(m)
            
    for f in final:
        previous_store[f] = timestamp
        
    return final
        

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            matches = get_wikidata_items(event["text"])
            matches = remove_recent(matches,float(event["ts"]))
            #print matches
            if matches:
                message = make_message(matches,event["text"])
                return message, event
            #if user_id == starterbot_id:
            #    return message, event["channel"]
    return None, None

def get_wikidata_items(message_text):
    """
    returns any Q or P items mentioned in a message
    if this is inside a URL, is ignored
    """
    MENTION_REGEX = "\\b([QPqp]\d+)"
    
    URL_REGEX = "(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?"
    
    urls = ["".join(x) for x in re.findall(URL_REGEX, message_text)]
    all_urls = "".join(urls)
    
    matches = re.findall(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    matches = [x for x in matches if x not in all_urls and x.lower() <> "p0"]
    
    if matches:
        return matches
    else:
        return []

def handle_command(command, event):
    """
    sends message to channel
    """
    # Finds and executes the given command, filling in response
    response = command
    position_args = {"channel":event["channel"]}
    
    if "thread_ts" in event:
        position_args["thread_ts"] = event["thread_ts"]
    #else:
    #    position_args["thread_ts"] = event["ts"] #force it reply threaded

    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        text=response,
        **position_args)
    
def bot_loop():
    if slack_client.rtm_connect():
        print("Wikidata bot connected and running!")
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
    bot_loop()