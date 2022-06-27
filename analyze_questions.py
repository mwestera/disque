import pandas as pd

import ling
import utils
import config
import tqdm

def main():
    tweets = utils.load_tweets(config.path_to_analyzed_tweets, max_num=config.max_num_rows)
    questions = extract_potential_questions(tweets)

    compute_features(questions)

    remove_nonquestions(questions)
    write_questions_to_csv(questions)

    explore_questions(questions)


def extract_potential_questions(tweets):
    keep_keys = ['created_at','favorite_count','retweet_count','dataset','language']
    new_rows = []
    for i, row in tweets.iterrows():
        potential_questions = ling.extract_potential_questions(row['full_text'], row['language'])
        for j, (question, offset) in enumerate(potential_questions):
            new_row = {(key if key in keep_keys else 'tweet_' + key): value for key, value in row.items()}

            new_row['id'] = 'Q' + str(row['id']) + '.' + str(j)
            new_row['text'] = utils.clean_sentence(question, row['language'])
            new_row['offset'] = offset  # TODO take cleaning into account...

            if not config.include_full_tweet_text_in_analyzed_questions_csv:
                del new_row['tweet_full_text']
                del new_row['tweet_quoted_text']

            new_rows.append(new_row)

    questions = pd.DataFrame(new_rows)

    return questions


def write_questions_to_csv(questions):
    del questions['spacy']  # don't save this
    columns_with_tweet_info_last = sorted(questions.columns, key=lambda x: x.startswith('tweet_') - (x in ['id', 'text']))
    questions.to_csv(config.path_to_analyzed_questions, columns=columns_with_tweet_info_last, index=False)


def compute_features(questions):
    spacy_parses = []
    for index, text, language in tqdm.tqdm(questions[['text', 'language']].itertuples(), total=len(questions), desc='Parsing all questions with Spacy'):
        nlp = utils.get_nlp_model(language)
        sentences = list(nlp(text).sents)
        sentence = sentences[-1]
        if len(sentences) > 1:
            questions.at[index, 'text'] = sentence.text
            questions.at[index, 'offset'] += sentence[0].idx
            sentence = list(nlp(sentence.text).sents)[0]   # TODO Not the most efficient
        spacy_parses.append(sentence)
    questions['spacy'] = spacy_parses

    questions['has_negation'] = [ling.has_negation(sent) for sent in questions['spacy']]
    questions['has_ref_to_other'] = [ling.has_references_to_other(sent) for sent in questions['spacy']]
    questions['has_ref_to_group'] = [ling.has_references_to_group(sent) for sent in questions['spacy']]
    questions['has_conjunction'] = [ling.has_conjunctions(sent) for sent in questions['spacy']]
    questions['has_leveler'] = [ling.has_levelers(sent) for sent in questions['spacy']]

    questions['has_question_mark'] = [text.strip('!').endswith('?') for text in questions['text']]
    questions['subj_verb_inversion'] = [sent._.has_inversion for sent in questions['spacy']]

    questions['structure'] = [sent._.qtype['structure'] for sent in questions['spacy']]
    questions['use'] = [sent._.qtype['use'] for sent in questions['spacy']]
    questions['qwords_literal'] = ['|'.join(sent._.qtype['wh_words_literal']) for sent in questions['spacy']]
    questions['qwords_functional'] = ['|'.join(sent._.qtype['wh_words_functional']) for sent in questions['spacy']]

    # questions['qwords'] = ['|'.join(tok.text for tok in sent if tok._.qtype != 'no') for sent in questions['spacy']]
    # questions['qword_types'] = [utils.qtypes_to_string(doc) for doc in questions['spacy']]


def remove_nonquestions(questions):
    """
    Remove any questions that neither end with a question mark, nor have a question-like wh-word (could be indirect
    question, i.e., lacking a question mark).
    """
    is_question = [qtype == 'no' for qtype in questions['use']]
    questions.drop(questions.loc[is_question].index, axis=0, inplace=True)


def explore_questions(questions):
    print('number of questions per dataset:')
    print(questions.groupby('dataset')['id'].count())

    print('\ncolumns and data types:')
    print(questions.dtypes)

    print('\nProportion of questions that has various features:')
    features_to_print = ['has_negation', 'has_ref_to_other', 'has_ref_to_group', 'has_conjunction', 'has_leveler', 'has_question_mark', 'subj_verb_inversion']
    print(questions.groupby('dataset')[features_to_print].mean().to_string())
    print()
    print(questions.groupby(['dataset', 'structure', 'use'])['id'].count().to_string())
    print()
    print(questions.groupby(['dataset', 'qwords_functional'])['id'].count().sort_values(key=lambda x: -x).head(10).to_string())
    print('          ... (showing only top 10)')



if __name__ == '__main__':
    main()