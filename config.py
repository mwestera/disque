

# Set this to a number to read only that many lines from a .csv file, for faster testing; otherwise, set to None.
max_num_rows = None

# You can analyze just one dataset or select multiple to analyze jointly:
paths_to_raw_tweets = {
    'dutch10K': 'data/dutch_tbcov_10K.csv',
    # 'french10K': 'data/french_tbcov_10K.csv',
    # 'italian10K': 'data/italian_tbcov_10K.csv',
    # 'dutch400K': 'data/dutch_tbcov_400k.csv'
}


# The files below will be created.
# Note: change these paths in case you don't want to overwrite them, i.e., keep multiple versions.

path_to_analyzed_tweets = 'data/analyzed_tweets.csv'

path_to_analyzed_questions = 'data/analyzed_questions.csv'

# You can set this to True, but the file will be bigger.
include_full_tweet_text_in_analyzed_questions_csv = False