import pandas as pd

import ling
import utils
import config


def main():

    tweets = utils.load_tweets(config.path_to_analyzed_tweets)

    tweets = tweets.loc[tweets['has_question']]  # restrict attention to tweets that have a question

    questions = make_one_row_per_question(tweets)

    compute_question_features(questions)
    explore_questions(questions)


def make_one_row_per_question(tweets):
    new_rows = []
    for i, row in tweets.iterrows():
        questions = ling.extract_questions(row['full_text'])
        for j, question in enumerate(questions):
            new_row = row.copy()    # contains all the tweet's data

            # add tweet_ prefix to all the old fields (tweet-level features, to not confuse them with question-level features)
            print(new_row)
            quit()

            new_row['question_id'] = int(str(new_row['id']) + str(j))
            new_row['question'] = question
            new_rows.append(new_row)
    return pd.DataFrame(new_rows)


def compute_question_features(questions):
    questions['question_has_negation'] = [ling.has_negation(question, language) for question, language in
                                          zip(questions['full_text'], questions['language'])]


def explore_questions(questions):
    print('number of questions per dataset:')
    print(questions.groupby('dataset')['question_id'].count())

    print('\ncolumns and data types:')
    print(questions.dtypes)

    print('\nProportion of questions that has a negation:')
    print(questions.groupby('dataset')['question_has_negation'].mean())
    print()

lbsalbdsalbdsalbdsa

wh_words = ['who', 'what', 'where', 'when', 'why', 'how']

def extract_matrix_question_words(question):
    """
    Extracts the wh-word(s) of a spacy-analyzed sentence, if any. Intended to return only
    'relevant' wh-words, i.e., that make the question a wh-question. Technically, it returns
    all the wh-words that are under the main verb, with no verb intervening. This is probably
    too simplistic (cf. island constraints on wh-movement in the syntax literature).
    """
    wh_words_found = []
    for tok in question:
        if tok.text.lower() in wh_words:
            for intermediate in get_path_to_root(question, tok)[1:-1]:
                if intermediate.pos_ == 'VERB':
                    break
            else:  # executed when for-loop is not 'break'ed, i.e., when no intermediate VERB node found
                wh_words_found.append(tok)
    return wh_words_found


def get_path_to_root(spacy_sent, node):
    """
    Take a spacy-analyzed sentence (not a full doc, for which 'root' is not defined) and return path
    from node to root (including the node and root themselves).
    """
    path = [node]
    while node != spacy_sent.root:
        node = node.head
        path.append(node)
    return path



if __name__ == '__main__':
    main()