import datetime
import pandas as pd
import re
import functools
import spacy


spacy_model_names = {
    'english': 'en_core_web_sm',
    'french': 'fr_core_news_sm',
    'italian': 'it_core_news_sm',
    'dutch': 'nl_core_news_sm',
}


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


@functools.lru_cache()
def regex_for_keyword_list(words):
    return re.compile('|'.join(rf'\b{key}\b' for key in words), flags=re.I)


@functools.lru_cache()
def get_nlp_model(language):
    nlp = spacy.load(spacy_model_names[language])
    return nlp


def spacy_single(s, language):
    return next(get_nlp_model(language)(s).sents)


def strip_mentions(text):
    return re.sub("@[A-Za-z0-9]+", "", text).strip()


def spacy_get_path_to_root(spacy_sent, node):
    """
    Take a spacy-analyzed sentence (not a full doc, for which 'root' is not defined) and return path
    from node to root (including the node and root themselves).
    """
    path = [node]
    while node != spacy_sent.root:
        node = node.head
        path.append(node)
    return path


def print_parse(doc):
    print(*[f'  {tok} {tok.pos_} ({tok.dep_} of {tok.head})' for tok in doc], sep='\n')