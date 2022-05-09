import pandas as pd

import ling
import utils
import config


def main():
    tweets = utils.load_tweets(config.path_to_analyzed_tweets, max_num=config.max_num_rows)
    questions = extract_questions(tweets)

    compute_features(questions)

    write_questions_to_csv(questions)

    explore_questions(questions)


def extract_questions(tweets):
    tweets = tweets.loc[tweets['has_question']]
    keep_keys = ['created_at','favorite_count','retweet_count','dataset','language']
    new_rows = []
    for i, row in tweets.iterrows():
        questions = ling.extract_questions(row['full_text'])
        for j, question in enumerate(questions):
            new_row = {(key if key in keep_keys else 'tweet_' + key): value for key, value in row.items()}

            new_row['id'] = 'Q' + str(row['id']) + '.' + str(j)
            new_row['text'] = question.strip()

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
    questions['has_negation'] = [ling.has_negation(text, language) for text, language in
                                          zip(questions['text'], questions['language'])]
    questions['spacy'] = [utils.spacy_single(text, language) for text, language in
                          zip(questions['text'], questions['language'])]
    questions['wh_word'] = [ling.extract_matrix_question_words(sent, language) for sent, language in
                          zip(questions['spacy'], questions['language'])]

    ... # More features to be added


def explore_questions(questions):
    print('number of questions per dataset:')
    print(questions.groupby('dataset')['id'].count())

    print('\ncolumns and data types:')
    print(questions.dtypes)

    print('\nProportion of questions that has a negation:')
    print(questions.groupby('dataset')['has_negation'].mean())
    print()



if __name__ == '__main__':
    main()