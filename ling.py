import re
import utils
import vocab


def has_negation(text, language):
    """
    Currently quite simplistic; could be made more syntactically aware   # TODO
    """
    return utils.has_any_keyword(vocab.negation_keywords[language], text)


sentence_pattern = r'[^.!?:;\n\t]+[?!.]+'
wh_word_pattern = {
    language: rf'\b{"|".join(vocab.wh_words[language] + vocab.wh_words_emb[language])}\b' for language in vocab.wh_words
}

def extract_potential_questions(text, language):
    for match in re.finditer(sentence_pattern, text):
        sentence = match.group()
        span = match.span()
        if sentence.strip('!').endswith('?') or any(match for match in re.finditer(wh_word_pattern[language], sentence)):
            yield sentence, span


verblike_pos_tags = ['AUX', 'VERB']
objectlike_dep_tags = ['dobj', 'obj', 'iobj', 'obl', 'obl:agent']
subjectlike_dep_tags = ['nsubj', 'nsubjpass', 'nsubj:pass', 'csubj', 'csubjpass', 'expl', 'expl:subj']


def wh_word_is_fronted(wh_word):
    """
    Intended only for wh-words; checks simply if any auxiliaries or verbs occur to the left.
    A consequence is that subjects in SVO are also considered fronted by default.
    """
    for lefthand_token in wh_word.sent[:wh_word.i]:
        if lefthand_token.pos_ in verblike_pos_tags:
            return False
    return True


def has_subj_verb_inversion(question):
    """
    Checks if root verb comes before subject, with special clause for copula + ADJ constructions,
    where the dependency parser treats the ADJ as the sentence root.
    TODO french: if starts with est-ce?
    """
    verb, subject = None, None
    # Weird parataxis misparse:   Hoorde[parataxis] je[nsubj of gekomen] wie er zijn gekomen?
    for tok in question:
        if tok.pos_ == 'VERB' and tok.dep_ == 'parataxis' and tok.i < len(question) - 1 and question[tok.i + 1].dep_ == 'nsubj':
            utils.log(f'{question} assumed inverted with weird parataxis misparse')
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
        utils.log(f'not inverted ({subject}, {verb})' if not inversion else f'inverted ({verb}, {subject})')
        return inversion

    utils.log(f'{question} inverted? don\'t know')


def is_potential_question_word(token):
    """
    Auxiliary for extract_matrix_question_words, to filter out some definitely-not-question-words
    based on simple language-specific rules (e.g., 'ce qui' in french relatives, never a question word).
    """
    language = utils.language_of(token)
    question = token.sent
    if token.text.lower() not in vocab.wh_words[language] + vocab.wh_words_emb[language]:
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
        if token.i > 2 and question[token.i-2].text.lower() == 'à' and question[token.i-1].text.lower() == 'ce':  # filter out French free relatives? actually, indirect questions can have this shape.
            return False
    return True


def is_question_word_for_indirect_only(token):
    language = utils.language_of(token)
    if token.text.lower() in vocab.wh_words_emb[language]:
        utils.log(f'{token} is fit for indirect questions only.')
        return True
    return False


def get_embedder_of(token):
    sent = token.sent

    actual_roots = [tok for tok in sent[:token.i] if tok.pos_ == 'VERB' and tok.dep_ in ['nsubj', 'parataxis']]
    if actual_roots and is_embedder(actual_roots[0]):
        utils.log(f'{token} has embedder {actual_roots[0]} because weird parataxis/nsubj misparse')
        # Hoorde [VERB, parataxis] je wie er zijn gekomen?
        # Weet [VERB, nsubj] Jan wie er zijn gekomen?
        # Il te [VERB, nsubj of dira] le dira quand ton frère?  --> still returns the wrong root though.
        return actual_roots[0]

    if token.dep_ == 'advmod' and token.head == sent.root and is_embedder(sent.root) and sent.root.i < token.i and might_be_complementizer(token): # and any(parataxa_or_ccomp)
        # Fixes some misparses:
        #   Il a dit pourquoi (advmod of dit) il l'a fait?
        #   weet (ROOT) je waarom (advmod of weet) jan sliep (parataxis)?
        #   Il a demandé quand[advmod of demandé]
        utils.log(f'{token} has embedder {sent.root} because advmod misparse')
        return sent.root

    if token.head.dep_ in ['obj', 'advcl', 'ccomp', 'acl:relcl'] and is_verblike(token.head) and is_embedder(token.head.head):
        # Wat er precies gebeurde[obj/advcl] heb ik niet kunnen zien/opnemen.
        # Wat hij deed[ccomp] vroeg ik hem[obj] al eerder.
        # Not: Wat hij deed[ccomp] veroorzaakte een ongeluk[obj].
        # Il a lu ce qui lui plait[acl:relcl]?
        utils.log(f'"{token}" has head.head "{token.head.head}" as embedder (via verblike obj/advl/ccomp)')
        return token.head.head

    for tok in utils.spacy_get_path_to_root(token)[2:]:
        if is_verblike(tok):
            utils.log(f'{token} has nearest verblike ancestor {tok} as embedder')
            return tok

    utils.log(f'{token} has no embedder')
    return None


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
    language = utils.language_of(token)
    if any(child.dep_ == 'mark' for child in token.head.children if child != token):
        utils.log(f'"{token}" is not complementizer, because there\'s another mark')
        return False
    if any(tok.lemma_ in vocab.neutral_pronouns[language] and tok.dep_ == 'obj' for tok in token.sent.root.children if tok != token):
        utils.log(f'"{token}" is not complementizer, because there\'s already an impersonal pronoun as obj of root')
        # Il te le [pron, obj of dira] dira quand ton frère? (even though misparsed)
        return False
    utils.log(f'"{token}" might be complementizer, as there is no alternative mark or impersonal pronoun as obj of root.')
    return True


def is_verblike(token):
    if token.pos_ == 'ADJ' and any(tok.dep_ == 'cop' for tok in token.children):
        return True
    return token.pos_ in ['VERB', 'AUX']


def is_addressee(token):
    if '2' in token.morph.get('Person'):
        return True
    return False

def is_speaker(token):
    if '1' in token.morph.get('Person'):
        return True
    return False

def is_existential(token):
    language = utils.language_of(token)
    return token.lemma_ in vocab.existential_quantifiers[language]

def is_impersonal(token):
    language = utils.language_of(token)
    return token.lemma_ in vocab.impersonals[language]

def is_like_who(token):
    language = utils.language_of(token)
    return token.lemma_ in vocab.who_like[language]

def is_negation(token):
    language = utils.language_of(token)
    return token.lemma_ in vocab.negation_keywords[language]


def corrected_lemma(token):
    lemma = token.lemma_.lower()

    if lemma in ['vragen', 'vraag']:
        compound_parts = [tok for tok in token.children if tok.dep_ == 'compound:prt']
        if any(compound_parts):
            lemma = compound_parts[0].lemma_ + '_' + lemma
    if lemma.startswith('af_') and not any(tok.lemma_ == 'af' for tok in token.children if tok.dep_ == 'compound:prt'):
        lemma = lemma.split('_')[1]

    if token.lemma_.lower() != lemma:
        utils.log(f'Corrected lemma from {token.lemma_} to {lemma}')

    return lemma


embedders = {
    language: vocab.verbs_like_see[language] + vocab.verbs_like_know[language] + vocab.verbs_like_wonder[language] + vocab.verbs_like_ask[language] + vocab.nouns_like_question[language]
    for language in vocab.verbs_like_see
}

def is_embedder(token):
    language = utils.language_of(token)
    lemma = corrected_lemma(token)
    if lemma in embedders[language]:
        utils.log(f'"{token}" is an embedder.')
        return True
    utils.log(f'"{token}" ({lemma}) is not an embedder.')
    return False


def likely_to_head_indirect_question(token):
    language = utils.language_of(token)
    # is_question = has_subj_verb_inversion(token.sent)
    is_question = token.sent.text.endswith('?')
    lemma = corrected_lemma(token)
    subjects = [tok for tok in token.sent if is_subject_of(tok, token)]

    existential_subject = any(is_existential(tok) for tok in subjects)
    impersonal_subject = any(is_impersonal(tok) for tok in subjects)
    who_subject = any(is_like_who(tok) for tok in subjects)
    speaker_subject = any(is_speaker(tok) for tok in subjects) or not subjects
    addressee_subject = any(is_addressee(tok) for tok in subjects)
    present_tense = is_present_tense(token)

    result = False

    if lemma in vocab.verbs_like_know[language]:
        if is_question and present_tense and (who_subject or addressee_subject or existential_subject or impersonal_subject):
            utils.log(f'Structure resembles: Does anyone know? You know? Who knows? Does someone know? Does one know?...')
            result = True
        elif not is_question and speaker_subject and any(is_negation(tok) or tok.lemma_ in vocab.verbs_like_want[language] for tok in token.children) and is_present_tense(token):
            utils.log(f'Structure resembles: I don\'t know / I want to know...')
            result = True
        else:
            utils.log(f'Verb "{token}" is like "know", but no subject/tense/structure fit for indirect question.')

    if lemma in vocab.verbs_like_see[language]:
        if is_question and not present_tense and (who_subject or addressee_subject or existential_subject):
            utils.log(f'Structure resembles: Did anyone see? Did you notice? Who saw? Did someone see? ...')
            result = True
        else:
            utils.log(f'Verb "{token}" is like "see", but no subject/tense/structure fit for indirect question.')

    if lemma in vocab.verbs_like_wonder[language]:
        if not is_question and (speaker_subject or impersonal_subject) and is_present_tense(token):
            utils.log(f'Structure resembles: I wonder/one wonders/makes you wonder...')
            result = True
        elif is_question and (existential_subject or impersonal_subject or addressee_subject) and is_present_tense(token):
            utils.log(f'Structure resembles: Does anyone wonder? Does one wonder? Do you wonder?')
            result = True
        else:
            utils.log(f'Verb "{token}" is like "wonder", but no subject/tense/structure fit for indirect question.')

    if lemma in vocab.nouns_like_question[language]:
        if not is_question and is_present_tense(token):
            utils.log(f'Structure resembles: It\'s a mystery...')
            result = True

    if lemma in vocab.verbs_like_ask[language]:
        utils.log(f'Verb "{token}" is like ask.')
        if not is_question and (existential_subject or speaker_subject or impersonal_subject):
            utils.log(f'Structure resembles: Someone asked / I asked / one asks')
            result = True

    if any(tok.pos_ == 'SCONJ' for tok in token.children if tok.i < token.i):
        # Aangezien je merkte...
        utils.log(f'Verb "{token}" preceded by SCONJ.')
        result = False

    if result:
        utils.log(f'{token} ({token.lemma_}) likely to head indirect question.')
    else:
        utils.log(f'{token} ({token.lemma_}) unlikely to head indirect question.')
    return result


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
    language = utils.language_of(token)
    if 'Fin' in token.morph.get('VerbForm') and 'Pres' in token.morph.get('Tense'):
        return True
    if 'Inf' in token.morph.get('VerbForm'):
        if any(tok.lemma_ in vocab.perfect_auxiliaries[language] for tok in token.children if tok.pos_ == 'AUX'):
            # e.g., "I have come", where come is misparsed as infinitive instead of part
            return False
        if all('Pres' in tok.morph.get('Tense') for tok in token.children if tok.pos_ == 'AUX'):
            return True
    if token.pos_ in ['ADJ']:
        if all('Pres' in tok.morph.get('Tense') for tok in token.children if tok.pos_ == 'AUX'):
            return True
    if 'Prog' in token.morph.get('Aspect'):
        if all('Pres' in tok.morph.get('Tense') for tok in token.children if tok.pos_ == 'AUX'):
            return True
    if 'Pres' in token.sent.root.morph.get('Tense') or not any('Past' in tok.morph.get('Tense') for tok in token.sent):
        # "Blijft voor mij een raadsel"
        return True
    return False


# def might_be_relcomp(token):
#     if token.pos == 'SCONJ':
#         verbose(f'{token} might be relcomp')
#         return True
#     # if token.head.dep_ == 'obl:mod':
#     #     # For weird french case: Il te le dira quand[sconj, mark of viendras] tu viendras[noun, obl:mod of dira].
#     #     return True
#     verbose(f'{token} cannot be relcomp')
#     return False


def might_be_initial_relclause(token):
    """
    >>> might_be_initial_relclause(utils.spacy_single('Wat hij deed was stom.', 'dutch')[0])
    True
    >>> might_be_initial_relclause(utils.spacy_single('Wat hij deed veroorzaakte een ongeluk.', 'dutch')[0])
    True
    >>> might_be_initial_relclause(utils.spacy_single('Ik vond wat hij deed niet leuk.', 'dutch')[2])
    True
    >>> might_be_initial_relclause(utils.spacy_single('Ik weet niet wat hij deed.', 'dutch')[3])
    False
    >>> might_be_initial_relclause(utils.spacy_single('Wat deed hij dan?', 'dutch')[0])
    False
    >>> might_be_initial_relclause(utils.spacy_single('Weet je wat hij deed?', 'dutch')[2])
    False
    >>> might_be_initial_relclause(utils.spacy_single('Wat was het dat hij deed?', 'dutch')[0])
    False
    >>> might_be_initial_relclause(utils.spacy_single('Wat dacht je dat hij zei?', 'dutch')[0])
    False
    >>> might_be_initial_relclause(utils.spacy_single('Wat er precies gebeurde heb ik niet kunnen zien.', 'dutch')[0])
    False
    >>> might_be_initial_relclause(utils.spacy_single('Wat er precies gebeurde heb ik niet kunnen opnemen.', 'dutch')[0])
    True
    >>> might_be_initial_relclause(utils.spacy_single('Wat er gebeurde was een wonder.', 'dutch')[0])
    True
    """
    if token.dep_ == 'ROOT':
        # Wat[ROOT] was het dat hij zag?
        return False
    if token.dep_ == 'nsubj' and token.head.dep_ == 'ROOT':
        # Wat veroorzaakte[ROOT] het dat hij deed?
        return False
    if token.head == token.sent.root:
        if any(tok.dep_ == 'cop' for tok in token.head.children):
            return True
        if any(any(tok2.dep_ == 'cop' for tok2 in tok.children) for tok in token.head.children if tok.dep_ == 'obj'):
            # Wat hij deed[ROOT] was stom[obj of deed].
            return True
    if token.head.dep_ in ['csubj', 'nsubj']:
        # Wat hij deed[csubj] veroorzaakte[ROOT] een storm.
        # Wat er gebeurde[nsubj] was een wonder[ROOT].
        return True
    return False


def classify_whword(token):
    if not is_potential_question_word(token):
        return 'no'
    embedded_under = get_embedder_of(token)
    can_be_direct = token.sent.text.endswith('?') and not is_question_word_for_indirect_only(token)
    if can_be_direct and wh_word_is_fronted(token) and not might_be_initial_relclause(token):
        return 'fronted'
    elif embedded_under and might_be_complementizer(token):
        if likely_to_head_indirect_question(embedded_under):
            return 'indirect'
    elif can_be_direct and not might_be_initial_relclause(token):
        return 'insitu' # or free relative?
    return 'no'


