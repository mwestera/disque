import re
import utils

# Hashtags to look for, indicative of disinformation:
# Note: Use lowercase only, as all hashtags in the data are now turned into lowercase:
disinfo_hashtags = {
    'english': ['hoax', 'plandemic'],
    'french': ['hoax'],
    'italian': ['hoax'],
    'dutch': ['hoax', 'plandemie']
}

# Keywords to look for in plain text, indicative of disinformation:
# (Currently just using the same as the hashtags; could be customized of course)
disinfo_keywords = disinfo_hashtags


negation_keywords = {
    'english': ['not', 'n\'t', 'no'],
    'french': ['ne', 'pas', 'non'],
    'italian': ['no', 'non'],
    'dutch': ['niet', 'geen', 'nope', 'nah', 'nee']
}

def has_negation(text, language):
    """
    Currently quite simplistic; could be made more syntactically aware
    """
    return utils.has_any_keyword(negation_keywords[language], text)


# defining a question as: sequence of anything other than ., !, ?, :, ;, newline, tab, followed by one or more question marks.
question_pattern = r'[^.!?:;\n\t]+\?+'

def extract_questions(text):
    """
    From a tweet's text, return the list of all questions it contains, using a regular expression pattern.
    """
    if '?' not in text:  # shortcut just to speed it up
        return []
    return re.findall(question_pattern, text)

