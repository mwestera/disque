import re
import utils
import logging

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
    # TODO Make more sophisticated, allowing for indirect questions.
    """
    if '?' not in text:  # shortcut just to speed it up
        return []
    return re.findall(question_pattern, text)



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

verblike_pos_tags = ['AUX', 'VERB']
objectlike_dep_tags = ['dobj', 'obj', 'iobj', 'obl', 'obl:agent']
subjectlike_dep_tags = ['nsubj', 'nsubjpass', 'nsubj:pass', 'csubj', 'csubjpass', 'expl', 'expl:subj']


def wh_word_is_fronted(question, wh_word):
    """
    Intended only for wh-words; checks simply if any auxiliaries or verbs occur to the left.
    A consequence is that subjects in SVO are also considered fronted by default.
    """
    for lefthand_token in question[:wh_word.i]:
        if lefthand_token.pos_ in verblike_pos_tags:
            return False
    return True


def has_subj_verb_inversion(question):
    """
    Checks if root verb comes before subject, with special clause for copula + ADJ constructions,
    where the dependency parser treats the ADJ as the sentence root.
    """
    verb, subject = None, None
    # Weird parataxis misparse:   Hoorde[parataxis] je[nsubj of gekomen] wie er zijn gekomen?
    for tok in question:
        if tok.pos_ == 'VERB' and tok.dep_ == 'parataxis' and tok.i < len(question) - 1 and question[tok.i + 1].dep_ == 'nsubj':
            logging.debug(f'{question} assumed inverted with weird parataxis misparse')
            return True

    finite_verbs = [tok for tok in question if tok.pos_ in verblike_pos_tags and 'Fin' in tok.morph.get('VerbForm')]
    for finite_verb in finite_verbs:
        for token in question:
            if is_subject_of(token, finite_verb) or is_subject_of(token, finite_verb.head):
                subject, verb = token, finite_verb
                break
        if verb and subject:
            break

    if verb and subject:
        inversion = verb.i < subject.i
        logging.debug(f'{question} inverted? {verb}, {subject}: {inversion}')
        return inversion

    logging.debug(f'{question} inverted? don\'t know')


language_map = {
    'nl': 'dutch',
    'fr': 'french',
    'it': 'italian',
    'en': 'english',
}

def is_potential_question_word(token):
    """
    Auxiliary for extract_matrix_question_words, to filter out some definitely-not-question-words
    based on simple language-specific rules (e.g., 'ce qui' in french relatives, never a question word).
    """
    language = language_map[token.doc.lang_]
    question = token.sent
    if token.text.lower() not in wh_words[language] + wh_words_emb[language]:
        return False
    # if token.text.lower() in wh_words_emb[language] and token.dep_ not in ['mark', 'cc']:
    #     ## cc/cconj is a misparse...
    #     return False
    if language == 'dutch':
        if token.i <= 1 and token.text.lower() == 'wat' and len(question) > token.i + 1 and question[token.i+1].text.lower() == 'een':    # filter out exclamatives (X wat een)
            return False
        # if right_neighbors and right_neighbors[0].text.lower() == 'er':     # Jan weet wie er is gevallen
        #     return True
    if language == 'french':
        if token.i > 2 and question[token.i-2].text.lower() == 'ce' and question[token.i-1].text.lower() == 'ce':  # filter out French free relatives? actually, indirect questions can have this shape.
            return False
    return True


def is_question_word_for_indirect_only(token):
    language = language_map[token.doc.lang_]
    return token.text.lower() in wh_words_emb[language]


def get_embedder_of(token):
    sent = token.sent
    # TODO Make sure to check how free relatives are treated. Wat hij deed was stom.
    if token.head.dep_ == 'advcl':  # Tell me if[mark] you arrived[advcl].
        logging.debug(f'{token} has no embedder because token.head.dep_ == "advcl"')
        return None
    actual_roots = [tok for tok in sent[:token.i] if tok.pos_ == 'VERB' and tok.dep_ in ['nsubj', 'parataxis']]
    if actual_roots:
        logging.debug(f'{token} has embedder {actual_roots[0]} because weird parataxis/nsubj misparse')
        # Hoorde [VERB, parataxis] je wie er zijn gekomen?
        # Weet [VERB, nsubj] Jan wie er zijn gekomen?
        # Il te [VERB, nsubj of dira] le dira quand ton frère?  --> TODO still returns the wrong root though.
        return actual_roots[0]
    # parataxa_or_ccomp = [tok for tok in sent.root.children if tok.dep_ in ['ccomp', 'parataxis'] and tok.pos_ == 'VERB']
    if token.dep_ == 'advmod' and token.head == sent.root and sent.root.i < token.i and might_be_complementizer(token): # and any(parataxa_or_ccomp)
        # Fixes some misparses:
        #   Il a dit pourquoi (advmod of dit) il l'a fait?
        #   weet (ROOT) je waarom (advmod of weet) jan sliep (parataxis)?
        #   Il a demandé quand[advmod of demandé]
        logging.debug(f'{token} has embedder {sent.root} because advmod misparse')
        return sent.root

    for tok in utils.spacy_get_path_to_root(token)[2:]:
        if is_verblike(tok):
            logging.debug(f'{token} has nearest verblike ancestor {tok} as embedder')
            return tok

    logging.debug(f'{token} has no embedder')
    return None


impersonal_pronouns = {
    'english': ['it', 'that'],
    'french': ['le', 'la', 'ça', 'l\''],   # 'ce' introduces too much error
    'italian': [],
    'dutch': ['het', 'dat', 'dit'],
}


def might_be_complementizer(token):
    """
    >>> sent = utils.spacy_single('John knows that who came?', 'english')
    >>> might_be_complementizer(sent[3])
    False

    >>> sent = utils.spacy_single('John knows who came?', 'english')
    >>> might_be_complementizer(sent[3])
    True

    >>> sent = utils.spacy_single('Il a demandé quand.', 'french')
    >>> might_be_complementizer(sent[3])
    True


    """
    if any(child.dep_ == 'mark' for child in token.head.children if child != token):
        logging.debug(f'{token} is not complementizer, because there\'s another mark')
        return False
    if any(tok.lemma_ in impersonal_pronouns[language_map[token.lang_]] and tok.dep_ == 'obj' for tok in token.sent.root.children if tok != token):
        logging.debug(f'{token} is not complementizer, because there\'s already an impersonal pronoun as obj of root')
        # Il te le [pron, obj of dira] dira quand ton frère? (even though misparsed)
        return False
    return True


def is_verblike(token):
    if token.pos_ == 'ADJ' and any(tok.dep_ == 'cop' for tok in token.children):
        return True
    return token.pos_ in ['VERB', 'AUX']


verbs_like_wonder = {
    'english': ['wonder', 'question', 'doubt', 'unsure', 'uncertain'],
    'french': ['demander'] + ['demande'],
    'italian': [],
    'dutch': ['af_vragen', 'onzeker'],
}

verbs_like_ask = {
    'english': ['ask'],
    'french': ['demander'] + ['demande'],
    'italian': [],
    'dutch': ['vragen'],
}

verbs_like_know = {
    'english': ['know', 'say', 'tell', 'understand', 'certain', 'sure'],
    'french': [],
    'italian': [],
    'dutch': ['weten', 'vertellen', 'zeggen', 'begrijpen', 'kennen', 'zeker'] + ['weet'],    # mis-lemmatized
}

verbs_like_see = {
    'english': ['notice', 'see', 'hear', 'feel', 'discover', 'find_out'],
    'french': [],
    'italian': [],
    'dutch': ['merken', 'zien', 'horen', 'voelen', 'ontdekken'] + ['hoorde', 'merkte'],
}

existential_quantifiers = {
    'english': ['anyone', 'someone', 'who'],
    'french': ['il'],
    'italian': [],
    'dutch': ['iemand', 'wie'],
}


impersonals = {
    'english': ['one', 'you'],
    'french': ['il'],
    'italian': [],
    'dutch': ['men', 'je'],
}

def is_addressee(token):
    if '2' in token.morph.get('Person'):
        return True
    return False


def is_speaker(token):
    if '1' in token.morph.get('Person'):
        return True
    return False


def is_existential(token):
    language = language_map[token.doc.lang_]
    if token.lemma_ in existential_quantifiers[language]:
        return True


def is_impersonal(token):
    language = language_map[token.doc.lang_]
    if token.lemma_ in impersonals[language]:
        return True


def is_negation(token):
    language = language_map[token.doc.lang_]
    return token.lemma_ in negation_keywords[language]


def corrected_lemma(token):
    lemma = token.lemma_.lower()

    if lemma in ['vragen', 'vraag']:
        compound_parts = [tok for tok in token.children if tok.dep_ == 'compound:prt']
        if any(compound_parts):
            lemma = compound_parts[0].lemma_ + '_' + lemma
    if lemma.startswith('af_') and not any(tok.lemma_ == 'af' for tok in token.children if tok.dep_ == 'compound:prt'):
        lemma = lemma.split('_')[1]

    if token.lemma_.lower() != lemma:
        logging.debug(f'Corrected lemma from {token.lemma_} to {lemma}')

    return lemma


def likely_to_head_indirect_question(token):
    language = language_map[token.doc.lang_]
    inverted = has_subj_verb_inversion(token.sent)
    lemma = corrected_lemma(token)
    if inverted:
        if any((is_addressee(tok) or is_existential(tok) or is_impersonal(tok)) and is_subject_of(tok, token) for tok in token.sent):
            if lemma in verbs_like_know[language] and is_present_tense(token):
                logging.debug(f'{token} likely to head indirect question, because addressee/existential/impersonal + present-tense know-like verb.')
                return True
            if lemma in verbs_like_see[language]:
                logging.debug(f'{token} likely to head indirect question, because addressee/existential/impersonal + see-like verb.')
                return True
        if any(is_existential(tok) and is_subject_of(tok, token) for tok in token.sent):
            if lemma in verbs_like_wonder[language] and is_present_tense(token):
                logging.debug(f'{token} likely to head indirect question, because existential + present-tense wonder-like verb.')
                return True
    else:
        if any(is_impersonal(tok) and is_subject_of(tok, token) for tok in token.sent):
            if lemma in verbs_like_wonder[language] and is_present_tense(token):
                logging.debug(f'{token} likely to head indirect question, because impersonal + present-tense wonder-like verb.')
                return True
        if any(is_speaker(tok) and is_subject_of(tok, token) for tok in token.sent):
            if lemma in verbs_like_wonder[language] and is_present_tense(token):
                logging.debug(f'{token} likely to head indirect question, because speaker + present-tense wonder-like verb.')
                return True
            if lemma in verbs_like_know[language] and any(is_negation(tok) for tok in token.children) and is_present_tense(token):
                logging.debug(f'{token} likely to head indirect question, because speaker + negation + present-tense know-like verb.')
                return True
        if lemma in verbs_like_ask[language]:
            logging.debug(f'{token} likely to head indirect question, because non-present, ask-like verb.')
            return True
    logging.debug(f'{token} ({token.lemma_}) unlikely to head indirect question because no positive cases matched.')
    return False


def is_subject_of(token, verb):
    if verb.dep_ == 'parataxis' and token.i == verb.i + 1 and token.dep_ in subjectlike_dep_tags:
        # weird parataxis misparse  Hoorde[parataxis] je[nsubj of gekomen] wie er zijn gekomen?
        return True
    if token not in verb.children:
        return False
    if token.dep_ in subjectlike_dep_tags:
        return True
    if token.dep_ == 'obj' and not any(tok.dep_ in subjectlike_dep_tags for tok in token.head.children):
        # common misparse, e.g., "Weet iemand[OBJ] of het vaccin veilig is?"
        return True
    return False


perfect_auxiliaries = {
    'english': ['have'],
    'french': ['être', 'avoir'],
    'italian': ['avere', 'essere'],
    'dutch': ['hebben', 'zijn'],
}


def is_present_tense(token):
    """
    >>> is_present_tense(utils.spacy_single('Are you coming?', 'english')[2])
    True
    >>> is_present_tense(utils.spacy_single('Were you coming?', 'english')[2])
    False
    >>> is_present_tense(utils.spacy_single('Have you come?', 'english')[2])    # FAILS
    False
    >>> is_present_tense(utils.spacy_single('Have you arrived?', 'english')[2])
    False
    >>> is_present_tense(utils.spacy_single('Did you come?', 'english')[2])
    False
    >>> is_present_tense(utils.spacy_single('Do you come?', 'english')[2])
    True
    >>> is_present_tense(utils.spacy_single('Will you arrive?', 'english')[2])
    False
    """
    if 'Fin' in token.morph.get('VerbForm') and 'Pres' in token.morph.get('Tense'):
        return True
    if 'Inf' in token.morph.get('VerbForm'):
        if any(tok.lemma_ in perfect_auxiliaries[language_map[tok.doc.lang_]] for tok in token.children if tok.pos_ == 'AUX'):
            # e.g., "I have come", where come is misparsed as infinitive instead of part
            return False
        if all('Pres' in tok.morph.get('Tense') for tok in token.children if tok.pos_ == 'AUX'):
            return True
    if 'Prog' in token.morph.get('Aspect'):
        if all('Pres' in tok.morph.get('Tense') for tok in token.children if tok.pos_ == 'AUX'):
            return True
    return False


def might_be_relative_clause(token):
    if token.pos == 'SCONJ':
        return True
    # if token.head.dep_ == 'obl:mod':
    #     # For weird french case: Il te le dira quand[sconj, mark of viendras] tu viendras[noun, obl:mod of dira].
    #     return True
    return False


def classify_whword(token):
    """
    Wie dacht Jan dat er waren?
    # TODO: exclude free relatives?
    """
    sentence = token.sent
    if not is_potential_question_word(token):
        return None
    logging.debug(f'CLASSIFY_WHWORD: {token.sent}, {token}')
    embedded_under = get_embedder_of(token)
    can_only_be_indirect = is_question_word_for_indirect_only(token)
    can_be_relative_clause = might_be_relative_clause(token)
    can_be_insitu = sentence.text.endswith('?')
    if wh_word_is_fronted(sentence, token) and not can_only_be_indirect:
        return 'fronted'
    elif not embedded_under:
        if can_be_insitu and not can_only_be_indirect and not can_be_relative_clause:
            return 'insitu'
    elif might_be_complementizer(token):
        if likely_to_head_indirect_question(embedded_under):
            return 'indirect'
    elif can_be_insitu and not can_only_be_indirect and not can_be_relative_clause:
        return 'insitu' # or free relative?


