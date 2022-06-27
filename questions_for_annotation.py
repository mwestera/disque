import os

import pandas as pd
import random
import utils
import config

random.seed(12345)

sample_size_per_class = 20
sample_size_per_feature = 50

# id,text,created_at,favorite_count,retweet_count,dataset,language,
# offset,has_negation,has_ref_to_other,has_ref_to_group,has_conjunction,
# has_leveler,has_question_mark,subj_verb_inversion,
# structure,use,qwords_literal,qwords_functional,
# tweet_id,tweet_hashtags,tweet_num_questions,tweet_has_question,tweet_has_disinfo_hashtags,
# tweet_has_disinfo_text,tweet_has_disinfo_text_or_hashtags,tweet_has_negation

path_to_analyzed_questions = config.path_to_analyzed_questions or f'{config.path_to_main_data_dir}/questions_{"_".join(config.paths_to_raw_tweets.keys())}.csv'
language = 'dutch'  # TODO get from config? abort if multiple languages selected?

# path_to_analyzed_questions, language = 'data/dutch_tbcov_3M_questions.csv', 'dutch'
max_n_chars_per_question = 70

dataset = pd.read_csv(path_to_analyzed_questions)

os.makedirs('data/annotation', exist_ok=True)

annotation_instructions = f"""// This file contains {language.capitalize()} questions with the predicted categories of wh-words and the questions as a whole.
// 1. Individual wh-words are tagged in square brackets like "who[no/insitu/fronted/indirect]"
//    - here 'indirect' means it is pragmatically likely to be used as an indirect question.
//    - embedded wh-words that are unlikely to be used as indirect questions, are tagged with 'no'.
// 2. The syntactic structure of each question as a whole is categorized at the end of each line as "polar/wh/insitu/elliptic/decl/risingdecl"
//    - here 'elliptic' is intended for non-wh-questions whose subject-verb order cannot be determined, typically because there is no matrix verb.
//    - 'wh' means a fronted-wh question; 'insitu' means an insitu-wh question; if a question has both, the former wins.

// Annotation instructions:
// If a line is mis-classified, please duplicate and correct it (both the wh-tags and the overall classification), and
// comment out the original line by prefixing "//"/. 
// To help me figure out what the current system is doing wrong, consider adding a "//"-comment at the end of a line briefly
// explaining what the problem might be (especially for languages I don't speak).

// {language}
"""

with open(f'data/annotation/{language}_classification.txt', 'w+') as file:
    file.write(annotation_instructions)
    for (structure, use), df in dataset.groupby(['structure', 'use']):
        # print('\n# Syntactic type:', structure, '   |  Pragmatic use:', use, 'question', end='\n - ')
        questions = set(df['text'].to_list())
        questions = [q for q in questions if len(q) < max_n_chars_per_question]
        sample = random.sample(questions, k=min(len(questions), sample_size_per_class))
        for question in sample:
            sent = utils.spacy_single(question, language, enforce_single_sentence=True)
            file.write(utils.doc_to_qtype_line(sent) + '\n')
            #
            # for qword in qwords_lit:
            #     question.find(qword)
            # print(*sample, sep='\n - ')

annotation_instructions = f"""// This file contains {language.capitalize()} questions, roughly equal number with and without the given feature.

// Annotation instructions:
// - If a line is mis-classified, prefix it with //. 
// - To help me figure out what the current system is doing wrong, consider also adding a "//"-comment at the end of the 
//   line, briefly explaining what the problem might be (especially for languages I don't speak).

"""

features = ['has_negation', 'has_ref_to_other', 'has_ref_to_group', 'has_conjunction', 'has_leveler']
for feature in features:
    with open(f'data/annotation/{language}_{feature.replace("_", "-")}.txt', 'w+') as file:
        file.write(annotation_instructions)
        for index, df in dataset.groupby(feature):
            file.write(f"\n\n// These questions are predicted to have {feature} == {index}:\n")
            questions = set(df['text'].to_list())
            questions = [q for q in questions if len(q) < max_n_chars_per_question]
            sample = random.sample(questions, k=min(len(questions), sample_size_per_feature))
            for question in sample:
                file.write(question + '\n')
