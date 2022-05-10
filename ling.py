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



wh_words = {
    'english': ['who', 'what', 'where', 'when', 'why', 'how'],
    'french': ['quoi', 'qui'],
    'italian': ['dove', 'quando'],
    'dutch': ['wie', 'wat', 'waar', 'wanneer', 'waarom', 'hoe', 'hoeveel', 'hoezeer', 'hoezo'],
}


def is_noncomplementizer_verb(token):
    """
    Auxiliary function, returns true if the token is a verb that has no explicit complementizer like 'that'.
    Used for determing wh-words, where, e.g., "John knows that who came?" is an in-situ wh-question,
    but "John knows who came?" typically isn't (though it can be... John knows WHO came?).
    """
    if token.pos_ != 'VERB':
        return False
    if any(child.dep_ == 'mark' for child in token.children):
        return False
    return True


verblike_pos_tags = ['AUX', 'VERB']
objectlike_dep_tags = ['dobj', 'obj', 'iobj', 'obl', 'obl:agent']
subjectlike_dep_tags = ['nsubj', 'nsubjpass', 'nsubj:pass', 'csubj', 'csubjpass', 'expl']


def wh_word_is_fronted(question, wh_word):
    """
    Intended only for wh-words; checks simply if any auxiliaries or verbs occur to the left.
    A consequence is that subjects in SVO are also considered fronted by default.
    """
    for lefthand_token in question[:wh_word.idx]:
        if lefthand_token.pos_ in verblike_pos_tags:
            return False
    return True


def has_subj_verb_inversion(question):
    """
    Checks if root verb comes before subject, with special clause for copula + ADJ constructions,
    where the dependency parser treats the ADJ as the sentence root.
    """
    if question.root.pos_ in verblike_pos_tags:
        for child in question.root.children:
            if child.dep_ in subjectlike_dep_tags:
                return question.root.idx < child.idx
    elif question.root.pos_ in ['ADJ']:     # ADJ like 'mooi' in 'het zou mooi zijn'
        verb, subject = None, None
        for child in question.root.children:
            if child.pos_ in verblike_pos_tags:
                verb = child
            elif child.dep_ in subjectlike_dep_tags:
                subject = child
            print(verb, subject)
            if verb and subject:
                return verb.idx < subject.idx


def definitely_not_question_word(token, question, language):
    """
    Auxiliary for extract_matrix_question_words, to filter out some definitely-not-question-words
    based on simple language-specific rules (e.g., 'ce qui' in french relatives, never a question word).
    """
    if token.text.lower() not in wh_words[language]:
        return True
    right_neighbors = question[token.idx+1:]
    left_neighbors = question[:token.idx]
    if language == 'dutch':
        if right_neighbors and right_neighbors[0].text.lower() == 'een':    # filter out exclamatives
            return True
        if right_neighbors and right_neighbors[0].text.lower() == 'er':     # Jan weet wie er is gevallen
            return True
    if language == 'french':
        if left_neighbors and left_neighbors[-1].text.lower() == 'ce':  # filter out French free relatives
            return True


def extract_matrix_question_words(question, language):
    """
    Returns a list of all the wh-words that are under the main verb, with no verbs intervening except complementizer
    verbs. With some special clauses to filter out problem cases I encountered (due to parser shortcomings).
    """
    fronted_wh_words = []
    in_situ_wh_words = []
    for token in question:
        if definitely_not_question_word(token, question, language):
            continue
        # if token in question.root.children and any(tok.dep_ == 'parataxis' and tok.idx < question.root.idx for tok in question.root.children):
        #     continue    # fixes some parataxis misparses; actually covered by the next one
        if sum(tok.dep_ in subjectlike_dep_tags for tok in question.root.children) >= 2:
            continue    # fixes some multi-subject misparses: Hoorde je wie er zijn gekomen? Weet Jan wie er zijn gekomen?
        if token.dep_ == 'advmod' and any(tok.dep_ == 'parataxis' for tok in question.root.children):
            continue    # crudely fixes a parataxis bug:  weet je waarom (advmod of weet) jan sliep?
        if any(is_noncomplementizer_verb(ancestor) for ancestor in utils.spacy_get_path_to_root(question, token)[1:-1]):
            continue
        if wh_word_is_fronted(question, token):
            fronted_wh_words.append(token)
        else:
            in_situ_wh_words.append(token)

    return fronted_wh_words, in_situ_wh_words

