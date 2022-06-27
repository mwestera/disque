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
Span.set_extension('has_inversion', default=None)
Span.set_extension('has_tag_question', default=None)
Span.set_extension('ends_with_question_mark', default=None)
Span.set_extension('matrix_verb', default=None)
Span.set_extension('matrix_subject', default=None)
Token.set_extension('corrected_lemma', default=None)
Span.set_extension('qtype', default=None)


@Language.component("inversion_detector")
def inversion_detector(doc):
    for sent in doc.sents:
        sent._.has_inversion = ling.has_subj_verb_inversion(sent)
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

@Language.component("sentence_concatenator")
def sentence_concatenator(doc):
    for token in doc:
        token.sent_start = False
    return doc


@Language.component("matrix_subj_verb_identifier")
def matrix_subj_verb_identifier(doc):
    for sent in doc.sents:
        ling.determine_matrix_subject_and_verb(sent)
    return doc


spacy_model_names = {   # TODO Make option in config.py to use fast vs slow models?
    # 'english': 'en_core_web_sm',
    'english': 'en_core_web_trf',
    # 'french': 'fr_core_news_sm',
    'french': 'fr_dep_news_trf',
    'italian': 'it_core_news_sm',
    'dutch': 'nl_core_news_sm',
    # 'dutch': 'nl_core_news_lg',
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


def has_any_tag(keywords, tags):
    if any(keyword in tags for keyword in keywords):
        return True
    return False


@functools.lru_cache()
def regex_for_keyword_list(*words):
    return re.compile('|'.join(rf'\b{key}\b' for key in words), flags=re.I)


@functools.lru_cache()
def get_nlp_model(language, single_sentence=False):
    nlp = spacy.load(spacy_model_names[language], disable='ner')
    if single_sentence:
        nlp.add_pipe("sentence_concatenator", before='parser')
    nlp.add_pipe("lemma_corrector")
    nlp.add_pipe("question_mark_detector")
    nlp.add_pipe("matrix_subj_verb_identifier")
    nlp.add_pipe("inversion_detector")
    nlp.add_pipe("tagquestion_detector")
    nlp.add_pipe("qword_tagger")
    nlp.add_pipe("question_classifier")
    return nlp


def spacy_single(s, language, enforce_single_sentence=False):
    nlp = get_nlp_model(language, single_sentence=enforce_single_sentence)
    sentences = list(nlp(s).sents)
    return sentences[-1]


sentencizers = {'english': 'en_core_web_sm',
    'french': 'fr_core_news_sm',
    'italian': 'it_core_news_sm',
    'dutch': 'nl_core_news_sm',
}

@functools.lru_cache()
def get_sentencizer(language):
    nlp = spacy.load(sentencizers[language], disable=['tagger', 'parser', 'ner'])
    nlp.add_pipe('sentencizer')
    return nlp


def quick_sentencize(text, language):
    nlp = get_sentencizer(language)
    doc = nlp(text)
    return doc.sents


def strip_mentions(text):
    return re.sub("@[A-Za-z0-9_]+", "", text).strip()


def normalize_hashtags(text):
    return re.sub("#", "", text).strip()


characters_to_delete = '➡️'
deletion_pattern = '|'.join(characters_to_delete)

def clean_sentence(text, language):
    text = strip_mentions(text)
    text = normalize_hashtags(text)
    text = re.sub(deletion_pattern, '', text)
    if language == 'french':
        text = re.sub(r'(?<=[A-Za-z])-(?=[A-Za-z])', r' -', text)
        text = re.sub(r'Ã©', r'é', text)    # TODO find more principled, encoding-related way
        text = re.sub(r'Ã', r'à', text)
    return text


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
        if tok._.qtype and tok._.qtype != 'no':
            qtypes.append(f'{tok.text}-{tok._.qtype}')
    return '|'.join(qtypes)


def print_parse(doc):
    print('Full parse for:', doc)
    print(*[f'  {tok} ({tok._.corrected_lemma}, {tok.pos_}, {tok.dep_} of {tok.head}) [{tok.morph}] <{tok._.qtype}>' for tok in doc], sep='\n')
    print('Question categorization:', doc[0].sent._.qtype)


def doc_to_qtype_line(doc):
    s = f'{doc.text} | {doc._.qtype["structure"]}'
    for tok in list(doc)[::-1]:
        if tok._.qtype:
            s = s[:tok.idx + len(tok)] + f'[{tok._.qtype}]' + s[tok.idx + len(tok):]
    return s

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