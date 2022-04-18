import pandas as pd  #  <-- if this gives a red squiggle in PyCharm, hover over it and click 'install'.
import datetime
import seaborn as sns   # <-- this too
import matplotlib.pyplot as plt
import re

DATASETS_TO_ANALYZE = [
    'dutch10K',
    'french10K',
    'italian10K',
]


paths = {
    'dutch10K': 'data/dutch_tbcov_10K.csv',
    'french10K': 'data/french_tbcov_10K.csv',
    'italian10K': 'data/italian_tbcov_10K.csv',
}


def main():
    """
    This is the first function that gets called, and that controlls everything else.
    """
    tweets = load_data(DATASETS_TO_ANALYZE)
    compute_features(tweets)
    explore(tweets)

    questions = make_one_row_per_question(tweets)
    questions['question_has_negation'] = questions['question']
    compute_question_features(questions)
    explore_questions(questions)


def read_hashtag_list(string):
    substrings = string.strip('[]').split(',')
    hashtags = [substring.strip('"\'') for substring in substrings]
    return hashtags


def load_data(datasets):
    """
    Loads each .csv file as a pandas 'dataframe' and concatenates them into one big dataframe.
    It creates a column 'dataset' with the label of the original dataset from which it came, to keep track.
    """
    all_tweets = []
    for key in datasets:
        tweets = pd.read_csv(paths[key], converters={'hashtags': read_hashtag_list})
        tweets['dataset'] = key
        tweets['language'] = '???'
        for language in ['dutch', 'italian', 'french', 'english']:
            if key.startswith(language):
                tweets['language'] = language
        all_tweets.append(tweets)
    all_tweets = pd.concat(all_tweets).reset_index(drop=True)
    return all_tweets



def compute_features(data):
    data['date'] = [extract_date(time) for time in data['created_at']]  # extract 'date' objects from the 'created_at' strings
    data['questions'] = [extract_questions(text) for text in data['full_text']]
    data['has_question'] = [questions != [] for questions in data['questions']]     # simply tests if the list of extracted questions is not empty.
    data['has_disinfo_hashtags'] = [has_disinfo_hashtags(tags, language) for tags, language in zip(data['hashtags'], data['language'])]
    data['has_disinfo_text'] = [has_disinfo_text(text, language) for text, language in zip(data['full_text'], data['language'])]
    data['has_disinfo_text_or_hashtags'] = data['has_disinfo_text'] | data['has_disinfo_hashtags']

    data['has_negation'] = [has_negation(text, language) for text, language in zip(data['full_text'], data['language'])]


def explore(data):
    """
    Print some basic info and show a histogram plot of the 'temporal coverage' of our datasets.
    """
    print('number of tweets per dataset:')
    print(data.groupby('dataset')['id'].count())

    print('\ncolumns and data types:')
    print(data.dtypes)  # int and float are numbers; object is anything else (including a string)

    print('\nProportion of tweets that has a question:')
    print(data.groupby('dataset')['has_question'].mean())
    print()

    print('\nProportion of tweets that has disinfo hashtags:')
    print(data.groupby('dataset')['has_disinfo_hashtags'].mean())
    print()

    print('\nProportion of tweets that has disinfo text keywords:')
    print(data.groupby('dataset')['has_disinfo_text'].mean())
    print()


    sns.histplot(data=data, x='date', hue='dataset', multiple='stack')
    plt.show()


    print('Some example tweets (where available):')
    for source in DATASETS_TO_ANALYZE:
        print('\n -', source)
        subdataset_disinfo = data.loc[(data['dataset'] == source) & data['has_disinfo_text_or_hashtags']]
        subdataset_notdisinfo = data.loc[(data['dataset'] == source) & ~data['has_disinfo_text_or_hashtags']]
        # data.loc[BLA] selects all rows of the dataframe where BLA is true.

        print(f' {source}, disinfo:')
        print_sample_tweets(subdataset_disinfo, 10)
        print(f'\n {source} not disinfo:')
        print_sample_tweets(subdataset_notdisinfo, 10)


def print_sample_tweets(dataset, n_tweets):
    n_tweets_to_print = min(n_tweets, len(dataset))
    subdataset_sample = dataset.sample(n=n_tweets_to_print)
    for text in subdataset_sample['full_text']:
        print('    -', text)


sentence_separators = re.compile(r'(?<=[^A-Z].[.?!]) +(?=[a-zA-Z])')


def extract_questions(text):
    """
    From a tweet's text, return the list of all questions it contains.
    This is done by splitting on 'sentence separators' defined with a rather mystical regular expression above
    (copy-pasted from somewhere), and then saving all sentences that end with a question mark.
    """
    if '?' in text:
        sentences = sentence_separators.split(text)
        questions = [sent for sent in sentences if sent.endswith('?')]
        return questions
    return []



def extract_date(time):
    """
    Read a date/time string with the format of our dataset, and turn it into a date object.
    """
    time = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
    return time.date()


disinfo_hashtags = {
    'english': ['hoax', 'plandemic'],
    'french': ['hoax'],
    'italian': ['hoax'],
    'dutch': ['hoax', 'plandemie']
}


def has_disinfo_hashtags(hashtags, language):
    """
    Return a boolean (True/False) indicating whether the tweet has hashtags indicative of disinformation.
    It is based on the lists of hashtags above: disinfo_hashtags.
    This is only a very simple squib.
    """
    for tag in disinfo_hashtags[language]:
        if tag in hashtags:
            return True
    return False


disinfo_keywords = disinfo_hashtags     # currently just using the same, could be customized of course


def has_disinfo_text(text, language):
    """
    Return a boolean (True/False) indicating whether the tweet's text is indicative of disinformation.
    It is based on the disinfo_keywords per language defined above.
    This is again only a very simple squib.
    Beware: It checks if a keyword is a substring of the text. This means that looking for a keyword 'man' will also
    match e.g. 'manual' and 'humane'. If you want to ignore such subword-matches, you'd have to first tokenize the text
    into separate words and then look for a match. Tokenizing millions of tweets can take a bit of time, so maybe stick
    with the simpler method for now.
    """
    for keyword in disinfo_keywords[language]:
        if keyword in text:
            return True
    return False


negation_keywords = {
    'english': ['not', 'n\'t', 'no'],
    'french': ['ne', 'pas', 'non'],
    'italian': ['no', 'non'],
    'dutch': ['niet', 'geen', 'nope', 'nah', 'nee']
}


def has_negation(text, language):
    for keyword in negation_keywords[language]:
        if keyword in text:
            return True
    return False


def make_one_row_per_question(data):
    new_rows = []
    for i, row in data.iterrows():
        for j, question in enumerate(row['questions']):
            new_row = row.copy()
            del new_row['questions']
            new_row['question_id'] = int(str(new_row['id']) + str(j))
            new_row['question'] = question
            new_rows.append(new_row)
    return pd.DataFrame(new_rows)


def compute_question_features(questions):
    questions['has_negation'] = [has_negation(question, language) for question, language in
                                 zip(questions['full_text'], questions['language'])]


def explore_questions(questions):
    print('number of questions per dataset:')
    print(questions.groupby('dataset')['question_id'].count())

    print('\ncolumns and data types:')
    print(questions.dtypes)

    print('\nProportion of questions that has a negation:')
    print(questions.groupby('dataset')['has_negation'].mean())
    print()



if __name__ == '__main__':
    main()