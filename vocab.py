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


# Following are based on the trainee document:

pronouns_other = {
    'english': ['he', 'him', 'she', 'her', 'they', 'them'],
    'french': ['tu', 'toi', 'il', 'elle', 'lui', 'ils', 'elles'],   # are we sure about 'il', can be impersonal...
    'italian': ['io', 'tu', 'lui', 'lei'],
    'dutch': ['hij', 'hem', 'zij', 'haar', 'zij', 'hen', 'hun', 'ze'],
}

pronouns_group = {
    'english': ['we', 'you', 'they', 'people', 'us'],  # you is hard to test
    'french': ['on', 'nous', 'vous'],
    'italian': ['voi', 'noi', 'loro'],
    'dutch': ['wij', 'jullie', 'zij', 'ze', 'men', 'ons', 'onze'],
}

conjunctions = {
    'english': ['and', 'or'],
    'french': ['et', 'ou'],
    'italian': ['e', 'o', 'oppure', 'o forse'],
    'dutch': ['en', 'of'],
}

levelers = {
    'english': ['everyone', 'always', 'everything', 'never', 'no one', 'nobody', 'nothing'],
    'french': ['tout le monde', 'toujours', 'tout', 'ne jamais', 'ne rien', 'ne personne'],
    'italian': ['tutti', 'sempre', 'tutto', 'mai', 'nessuno', 'niente'],
    'dutch': ['iedereen', 'altijd', 'alles', 'nooit', 'niemand', 'niets', 'niks'],
}

negations = {   # TODO shouldn't we include negative quantifiers here?
    'english': ['not', 'n\'t', 'no'],
    'french': ['ne pas', 'n\' pas', 'non'],
    'italian': ['no', 'non'],
    'dutch': ['niet', 'geen'],
}


wh_words = {
    'english': ['who', 'what', 'how', 'why', 'which', 'when', 'where'], # 'how much', 'how many'?
    'french': ['que', "qu'", 'quoi', 'qui', 'quand', 'comment', 'combien', 'pourquoi', 'où'],
    'italian': ['cosa', 'chi', 'come', 'quanto', 'perché'], # also 'dove'?  # also non + statement + question mark
    'dutch': ['wie', 'wat', 'hoe', 'hoezo', 'waarom', 'welke', 'wanneer', 'hoeveel', 'waar', 'hoezeer'],    # waarnaar? waartoe?
}

# End of vocab based on the trainee document


wh_words_only_embedded = {
    'english': ['if', 'whether'],
    'french': ['si'],
    'italian': ['se'],
    'dutch': ['of'],
}

who_like = {
    'english': ['who'],
    'french': ['qui'],
    'italian': ['chi'],
    'dutch': ['wie'],
}

personal_existentials = {
    'english': ['anyone', 'someone'],
    'french': ['quelqu\'un', 'quelqu\'une'],
    'italian': ['qualcuna', 'qualcuno', 'chiunque'],
    'dutch': ['iemand'],
}

impersonals = {
    'english': ['one', 'you', 'people'],
    'french': ['il', 'gens'],
    'italian': ['gente'],  # Italian uses passive for this?
    'dutch': ['men', 'je', 'mensen'],
}

neutral_pronouns = {
    'english': ['it', 'that'],
    'french': ['le', 'la', 'ça', 'l\''],   # 'ce' introduces too much error
    'italian': ['l\'', 'lo', 'la'],
    'dutch': ['het', 'dat', 'dit'],
}


verbs_like_wonder = {
    'english': ['wonder', 'question', 'doubt', 'unsure', 'uncertain', 'curious'],
    'french': ['questionner', 'demander', 'douter', 'incertain', 'curieux'] + ['demande', 'questionne'],
    'italian': ['chierdersi', 'dubitare', 'incerto', 'incerta'],
    'dutch': ['af_vragen', 'onzeker', 'benieuwd', 'nieuwsgierig'],
}

nouns_like_question = {
    'english': ['mystery', 'question', 'puzzle'],
    'french': ['mystère', 'question', 'casse-tête'],
    'italian': ['mistero', 'domanda', 'enigma'],
    'dutch': ['vraag', 'mysterie', 'raadsel']
}

verbs_like_ask = {
    'english': ['ask', 'request'],
    'french': ['demander'] + ['demande'],
    'italian': ['richiedere', 'chiedere', 'domandare'],
    'dutch': ['vragen'],
}

verbs_like_know = {
    'english': ['know', 'say', 'tell', 'understand', 'certain', 'sure', 'see'],
    'french': ['dire', 'savoir', 'comprendre', 'certain', 'voir'],
    'italian': ['sapere', 'dire', 'raccontare', 'capire', 'certo', 'sicuro', 'vedere'],
    'dutch': ['weten', 'vertellen', 'zeggen', 'begrijpen', 'kennen', 'zeker', 'zien', 'inzien'] + ['weet'],    # mis-lemmatized
}

verbs_like_see = {
    'english': ['notice', 'see', 'hear', 'feel', 'discover', 'find_out', 'read'],
    'french': ['remarquer', 'voir', 'entendre', 'sentir', 'découvrir', 'trouver', 'lire'],
    'italian': ['notare', 'vedere', 'sentire', 'sentire', 'scoprire', 'leggere'],
    'dutch': ['merken', 'zien', 'horen', 'voelen', 'ontdekken', 'opnemen', 'lezen'] + ['hoorde', 'merkte'],
}

verbs_like_want = {
    'english': ['want', 'like', 'desire'],
    'french': ['vouloir', 'veux', 'désirer', 'voudrais'],
    'italian': ['voler', 'desiderare'],
    'dutch': ['willen', 'wensen'],
}

perfect_auxiliaries = {
    'english': ['have'],
    'french': ['être', 'avoir'],
    'italian': ['avere', 'essere'],
    'dutch': ['hebben', 'zijn'],
}