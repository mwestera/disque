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
    'english': ['not', 'n\'t', 'no', 'nobody', 'noone'],
    'french': ['ne', 'pas', 'non'],
    'italian': ['no', 'non'],
    'dutch': ['niet', 'geen', 'nope', 'nah', 'nee', 'niemand']
}


perfect_auxiliaries = {
    'english': ['have'],
    'french': ['être', 'avoir'],
    'italian': ['avere', 'essere'],
    'dutch': ['hebben', 'zijn'],
}


wh_words = {
    'english': ['who', 'what', 'where', 'when', 'why', 'how'],
    'french': ['quoi', 'qui', 'quand', 'pourquoi', 'que'],  # also qu' ?
    'italian': ['dove', 'quando'],
    'dutch': ['wie', 'wat', 'waar', 'wanneer', 'waarom', 'hoe', 'hoeveel', 'hoezeer', 'hoezo'],
}

wh_words_emb = {
    'english': ['if', 'whether'],
    'french': ['si'],
    'italian': [],
    'dutch': ['of'],
}



verbs_like_wonder = {
    'english': ['wonder', 'question', 'doubt', 'unsure', 'uncertain', 'curious'],
    'french': ['demander'] + ['demande'],
    'italian': [],
    'dutch': ['af_vragen', 'onzeker', 'benieuwd', 'nieuwsgierig'],
}

nouns_like_question = {
    'english': ['mystery', 'question'],
    'french': [],
    'italian': [],
    'dutch': ['vraag', 'mysterie', 'raadsel']
}

verbs_like_ask = {
    'english': ['ask'],
    'french': ['demander'] + ['demande'],
    'italian': [],
    'dutch': ['vragen'],
}

verbs_like_know = {
    'english': ['know', 'say', 'tell', 'understand', 'certain', 'sure', 'see'],
    'french': ['dire'],
    'italian': [],
    'dutch': ['weten', 'vertellen', 'zeggen', 'begrijpen', 'kennen', 'zeker', 'zien', 'inzien'] + ['weet'],    # mis-lemmatized
}

verbs_like_see = {
    'english': ['notice', 'see', 'hear', 'feel', 'discover', 'find_out'],
    'french': ['voir', 'lire'],
    'italian': [],
    'dutch': ['merken', 'zien', 'horen', 'voelen', 'ontdekken', 'opnemen'] + ['hoorde', 'merkte'],
}

verbs_like_want = {
    'english': ['want', 'like'],
    'french': ['vouloir', 'veux', 'voudrais'],
    'italian': [],
    'dutch': ['willen'],
}

existential_quantifiers = {
    'english': ['anyone', 'someone'],
    'french': [],
    'italian': [],
    'dutch': ['iemand'],
}

who_like = {
    'english': ['who'],
    'french': ['qui'],
    'italian': [],
    'dutch': ['wie'],
}

impersonals = {
    'english': ['one', 'you'],
    'french': ['il'],
    'italian': [],
    'dutch': ['men', 'je'],
}

neutral_pronouns = {
    'english': ['it', 'that'],
    'french': ['le', 'la', 'ça', 'l\''],   # 'ce' introduces too much error
    'italian': [],
    'dutch': ['het', 'dat', 'dit'],
}