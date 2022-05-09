import datetime
import pandas as pd
import re
import config
import functools

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
    hashtags = [substring.strip('"\'').lower() for substring in substrings]     # lowercased
    return hashtags


def load_tweets(path, max_num=None):
    return pd.read_csv(path, converters={'hashtags': parse_hashtag_list, 'created_at': parse_date}, nrows=max_num)


def has_any_keyword(keywords, text):
    pattern = regex_for_keyword_list(tuple(keywords))  # the tuple is unfortunate...
    if pattern.search(text):
        return True
    return False


@functools.lru_cache()  # slight speedup
def regex_for_keyword_list(words):
    return re.compile('|'.join(rf'\b{key}\b' for key in words), flags=re.I)
