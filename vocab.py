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

conjunctions = {    # TODO What about 'but', 'however', etc? And subordinating conjunctions? Don't those count?
    'english': ['and', 'or'],
    'french': ['et', 'ou'],
    'italian': ['e', 'o', 'oppure', 'o forse'],
    'dutch': ['en', 'of'],
}

levelers = {
    'english': ['everyone', 'always', 'everything', 'never', 'no one', 'nobody', 'nothing'],
    'french': ['tout le monde', 'toujours', 'tout', 'jamais', 'rien', 'personne'], # TODO Any reason to check for "ne ..." here?
    'italian': ['tutti', 'sempre', 'tutto', 'mai', 'nessuno', 'niente'],
    'dutch': ['iedereen', 'altijd', 'alles', 'nooit', 'niemand', 'niets', 'niks'],
}

negations = {
    'english': ['not', 'n\'t', 'no'],
    'french': ['non', 'pas'],  # TODO Is there any real reason to check for the "ne ..." prefix too?
    'italian': ['no', 'non'],
    'dutch': ['niet', 'geen'],
}


wh_words = {
    'english': ['who', 'what', 'how', 'why', 'which', 'when', 'where'], # 'how much', 'how many'?
    'french': ['que', "qu'", 'quoi', 'qui', 'quand', 'comment', 'combien', 'pourquoi', 'où'],
    'italian': ['cosa', 'chi', 'come', 'quanto', 'perché'], # also 'dove'?  # also non + statement + question mark
    'dutch': ['wie', 'wat', 'hoe', 'hoezo', 'waarom', 'welke', 'wanneer', 'hoeveel', 'waar', 'hoezeer', 'waaraan', 'waartoe', 'waarnaar', 'waarnaartoe', 'waarvan', 'vanwaar'],    # waarnaar? waartoe?
}

# End of vocab based on the trainee document


wh_words_only_embedded = {
    'english': ['if', 'whether'],
    'french': ['si'],
    'italian': ['se'],
    'dutch': ['of'],
}

wh_words_all = {
    language: wh_words[language] + wh_words_only_embedded[language] for language in wh_words
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
    'english': ['know', 'say', 'tell', 'understand', 'certain', 'sure', 'see', 'remember'],
    'french': ['dire', 'savoir', 'comprendre', 'certain', 'voir'],  # add remember
    'italian': ['sapere', 'dire', 'raccontare', 'capire', 'certo', 'sicuro', 'vedere'], # add remember
    'dutch': ['weten', 'vertellen', 'zeggen', 'begrijpen', 'kennen', 'zeker', 'zien', 'inzien', 'herinneren'] + ['weet'],    # mis-lemmatized
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

some_other_embedders = { # not reliable predictors of indirect questions, but still possible embedders
    'english': ['crazy', 'weird', 'strange', 'suspicious', 'funny'],
    'french': ['bizarre', 'étrange', 'suspect', 'suspecte'],
    'italian': ['strano', 'sospettoso', 'pazza', 'strana', 'sospettosa'],
    'dutch': ['gek', 'raar', 'vreemd', 'verdacht', 'grappig'],
}

all_embedders = {
    language: verbs_like_see[language] + verbs_like_know[language] + verbs_like_wonder[language] + verbs_like_ask[language] + nouns_like_question[language] + some_other_embedders[language]
    for language in verbs_like_see
}

perfect_auxiliaries = {
    'english': ['have'],
    'french': ['être', 'avoir'],
    'italian': ['avere', 'essere'],
    'dutch': ['hebben', 'zijn'],
}

tag_questions = {
    'english': ['right'],
    'italian': ['vero', 'giusto', 'no', 'eh'],
    'french': ['non'],
    'dutch': ['toch', 'niet waar'],
}
