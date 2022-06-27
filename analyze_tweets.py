import collections
import itertools

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

import utils
import ling
import config
import vocab


def main():
    """
    This is the first function that gets called, and that controls everything else.
    """

    path_to_analyzed_tweets = config.path_to_analyzed_tweets or f'{config.path_to_main_data_dir}/tweets_{"_".join(config.paths_to_raw_tweets.keys())}.csv'
    print('Analyzed tweets will be written to:', path_to_analyzed_tweets)

    tweets = load_raw_tweets(config.paths_to_raw_tweets)
    compute_features(tweets)
    tweets.to_csv(path_to_analyzed_tweets, index=False)
    explore(tweets)


def load_raw_tweets(dataset_paths):
    """
    Loads each .csv file as a pandas 'dataframe' and concatenates them into one big dataframe.
    It creates a column 'dataset' with the label of the original dataset from which it came, to keep track.
    """
    all_tweets = []
    for name, path in dataset_paths.items():
        tweets = utils.load_tweets(path, max_num=config.max_num_rows)
        tweets['full_text'] = tweets['full_text'].str.replace('\\r', ' ', regex=True).str.replace('   +', '\t', regex=True)
        tweets['quoted_text'] = tweets['quoted_text'].str.replace('\\r', ' ', regex=True).str.replace('   +', '\t', regex=True)
        tweets['dataset'] = name
        tweets['language'] = '???'
        for language in ['dutch', 'italian', 'french', 'english']:
            if name.startswith(language):
                tweets['language'] = language
        all_tweets.append(tweets)
    all_tweets = pd.concat(all_tweets).reset_index(drop=True)
    return all_tweets


def compute_features(tweets):
    tweets['num_questions'] = [text.count('?') for text in zip(tweets['full_text'])]

    tweets['has_question'] = [n > 0 for n in tweets['num_questions']]

    tweets['has_disinfo_hashtags'] = [utils.has_any_tag(vocab.disinfo_hashtags[language], tags) for tags, language in zip(tweets['hashtags'], tweets['language'])]

    tweets['has_disinfo_text'] = [utils.has_any_keyword(vocab.disinfo_hashtags[language], text) for text, language in zip(tweets['full_text'], tweets['language'])]

    tweets['has_disinfo_text_or_hashtags'] = tweets['has_disinfo_text'] | tweets['has_disinfo_hashtags']

    tweets['has_negation'] = [ling.has_negation(text, language)
                              for text, language in zip(tweets['full_text'], tweets['language'])]


def explore(tweets):
    """
    Print some basic info and show a histogram plot of the 'temporal coverage' of our datasets.
    """
    print('number of tweets per dataset:')
    print(tweets.groupby('dataset')['id'].count())

    print('\ncolumns and data types:')
    print(tweets.dtypes)  # int and float are numbers; object is anything else (including a string)

    print('\nProportion of tweets that has a question:')
    print(tweets.groupby('dataset')['has_question'].mean())
    print()

    print('\nProportion of tweets that has disinfo hashtags:')
    print(tweets.groupby('dataset')['has_disinfo_hashtags'].mean())
    print()

    print('\nProportion of tweets that has disinfo text keywords:')
    print(tweets.groupby('dataset')['has_disinfo_text'].mean())
    print()

    sns.histplot(data=tweets, x='created_at', hue='dataset', multiple='stack')
    plt.show()


    print('Some example tweets (where available):')
    for source in tweets['dataset'].unique():
        print('\n -', source)
        subdataset_disinfo = tweets.loc[(tweets['dataset'] == source) & tweets['has_disinfo_text_or_hashtags']]
        subdataset_notdisinfo = tweets.loc[(tweets['dataset'] == source) & ~tweets['has_disinfo_text_or_hashtags']]
        # data.loc[BLA] selects all rows of the dataframe where BLA is true.

        print(f' {source}, disinfo:')
        print_sample_tweets(subdataset_disinfo, 10)
        print(f'\n {source} not disinfo:')
        print_sample_tweets(subdataset_notdisinfo, 10)

    print('')
    for dataset, subdf in tweets.groupby('dataset'):
        print(f"Most frequent hashtags in {dataset}:")
        print(collections.Counter(itertools.chain(*subdf['hashtags'])).most_common(100))




def print_sample_tweets(tweets, num):
    n_tweets_to_print = min(num, len(tweets))
    subdataset_sample = tweets.sample(n=n_tweets_to_print)
    for text in subdataset_sample['full_text']:
        print('    -', text)


if __name__ == '__main__':
    main()