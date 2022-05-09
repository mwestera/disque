import re


disinfo_hashtags = {
    'english': ['hoax', 'plandemic'],
    'french': ['hoax'],
    'italian': ['hoax'],
    'dutch': ['hoax', 'plandemie']
}

disinfo_keywords = disinfo_hashtags     # currently just using the same, could be customized of course


negation_keywords = {
    'english': ['not', 'n\'t', 'no'],
    'french': ['ne', 'pas', 'non'],
    'italian': ['no', 'non'],
    'dutch': ['niet', 'geen', 'nope', 'nah', 'nee']
}

def has_negation(text, language):
    """
    Very simplistic; could be made less syntactically naive
    """
    for keyword in negation_keywords[language]:
        if keyword in text:
            return True
    return False


question_pattern = r'[^.!?\n]+\?+'

def extract_questions(text):
    """
    From a tweet's text, return the list of all questions it contains, using a regular expression pattern.
    """
    if '?' not in text:  # shortcut just to speed it up
        return []
    return re.findall(question_pattern, text)
