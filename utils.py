import datetime
import pandas as pd
import re

def parse_date(s):
    """
    Read a date/time string with the format of our dataset, and turn it into a date object.
    """
    try:
        time = datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            time = datetime.datetime.strptime(s, '%Y-%m-%d')
        except ValueError:
            return None
    return time.date()


def parse_hashtag_list(string):
    substrings = string.strip('[]').split(',')
    hashtags = [substring.strip('"\'').lower() for substring in substrings]
    return hashtags


def load_tweets(path):
    return pd.read_csv(path, converters={'hashtags': parse_hashtag_list, 'created_at': parse_date})


def has_any_keyword(text, keywords):
    pattern = '|'.join(rf'\b{keyword}\b' for keyword in keywords)
    if re.search(pattern, text):
        return True
    return False
