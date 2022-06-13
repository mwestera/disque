import datetime
import pandas as pd
import re
import functools
import spacy
from spacy.tokens import Token, Doc, Span
from spacy.language import Language
import ling

VERBOSE = False

Token.set_extension('qtype', default=None)
Token.set_extension('is_fronted', default=False)
Span.set_extension('has_inversion', default=None)
Span.set_extension('has_tag_question', default=None)
Span.set_extension('ends_with_question_mark', default=None)
Token.set_extension('corrected_lemma', default=None)
Span.set_extension('qtype', default=None)


@Language.component("inversion_detector")
def inversion_detector(doc):
    for sent in doc.sents:
        sent._.has_inversion = ling.has_subj_verb_inversion(doc)
    return doc

@Language.component("tagquestion_detector")
def tag_detector(doc):
    for sent in doc.sents:
        sent._.has_tag_question = ling.ends_with_tag_question(sent)
    return doc

@Language.component("lemma_corrector")
def lemma_corrector(doc):
    for tok in doc:
        tok._.corrected_lemma = ling.corrected_lemma(tok)
    return doc

@Language.component("frontedness_detector")
def frontedness_detector(doc):
    for sent in doc.sents:
        ling.mark_tokens_as_fronted(sent)
    return doc

@Language.component("question_mark_detector")
def question_mark_detector(doc):
    for sent in doc.sents:
        sent._.ends_with_question_mark = ling.ends_with_question_mark(sent)
    return doc

@Language.component("qword_tagger")
def qword_tagger(doc):
    for tok in doc:
        tok._.qtype = ling.classify_whword(tok)
    return doc

@Language.component("question_classifier")
def question_classifier(doc):
    for sent in doc.sents:
        sent._.qtype = ling.classify_question(sent)
    return doc


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
    hashtags = [substring.strip(' "\'').lower() for substring in substrings]     # lowercased
    hashtags = [t for t in hashtags if t]
    return hashtags


def load_tweets(path, max_num=None):
    dataframe = pd.read_csv(path, converters={'hashtags': parse_hashtag_list, 'created_at': parse_date}, nrows=max_num)
    dataframe[['full_text', 'quoted_text']] = dataframe[['full_text', 'quoted_text']].fillna('')
    return dataframe


def has_any_keyword(keywords, text):
    pattern = regex_for_keyword_list(*keywords)
    if pattern.search(text):
        return True
    return False


@functools.lru_cache()
def regex_for_keyword_list(*words):
    return re.compile('|'.join(rf'\b{key}\b' for key in words), flags=re.I)


@functools.lru_cache()
def get_nlp_model(language):
    nlp = spacy.load(spacy_model_names[language])
    nlp.add_pipe("lemma_corrector")
    nlp.add_pipe("question_mark_detector")
    nlp.add_pipe("frontedness_detector")
    nlp.add_pipe("inversion_detector")
    nlp.add_pipe("tagquestion_detector")
    nlp.add_pipe("qword_tagger")
    nlp.add_pipe("question_classifier")
    ling.language = language
    return nlp


def spacy_single(s, language):
    return list(get_nlp_model(language)(s).sents)[-1]


def strip_mentions(text):
    return re.sub("@[A-Za-z0-9]+", "", text).strip()


def spacy_get_path_to_root(node):
    """
    Take a spacy-analyzed sentence (not a full doc, for which 'root' is not defined) and return path
    from node to root (including the node and root themselves).
    """
    path = [node]
    while node != node.sent.root:
        node = node.head
        path.append(node)
    return path


def qtypes_to_string(doc):
    qtypes = []
    for tok in doc:
        if tok._.qtype != 'no':
            qtypes.append(f'{tok.text}-{tok._.qtype}')
    return '|'.join(qtypes)


def print_parse(doc):
    print('Full parse for:', doc)
    print(*[f'  {tok} ({tok._.corrected_lemma}, {tok.pos_}, {tok.dep_} of {tok.head}) [{tok.morph}] <{tok._.qtype}>' for tok in doc], sep='\n')
    print('Question categorization:', doc[0].sent._.qtype)


def log(s):
    if VERBOSE:
        print('  >', s)


language_map = {
    'nl': 'dutch',
    'fr': 'french',
    'it': 'italian',
    'en': 'english',
}

def language_of(token):  # also works on doc object...
    return language_map[token.doc.lang_]