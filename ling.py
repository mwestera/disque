import re
import utils
import vocab

sentence_pattern = r'[^.!?:;\n\t]+[?!.]+'

def extract_potential_questions(text, language):
    for match in re.finditer(sentence_pattern, text):
        sentence = match.group()
        span = match.span()
        if sentence.strip('!').endswith('?') or utils.has_any_keyword(vocab.wh_words_all[language], sentence):
            yield sentence, span

verblike_pos_tags = ['AUX', 'VERB']
objectlike_dep_tags = ['dobj', 'obj', 'iobj', 'obl', 'obl:agent']
subjectlike_dep_tags = ['nsubj', 'nsubjpass', 'nsubj:pass', 'csubj', 'csubjpass', 'expl', 'expl:subj']
misparsed_subject_dep_tags = ['nmod:poss', 'obj']

def ends_with_question_mark(sent):
    return sent.text.strip('!').endswith('?')


def mark_tokens_as_fronted(doc):
    """
    Simplifying, anything preceded only by conjunctions counts as 'fronted'.
    """
    for tok in doc:
        tok._.is_fronted = True
        if is_verblike(tok): # not in ['CCONJ', 'SCONJ']:
            break


def is_rising_declarative(sentence):
    if sentence._.ends_with_question_mark and not sentence._.has_inversion:
        utils.log('Sentence seems like a rising declarative.')
        return True
    return False


def has_subj_verb_inversion(sentence):
    """
    Checks if root verb comes before subject, or check for 'est-ce' in French, and with special clause for
    copula + ADJ constructions, where the dependency parser treats the ADJ as the sentence root.
    """
    language = utils.language_of(sentence)
    if language == 'french' and 'est-ce' in sentence.text.lower()[:20]:
        utils.log(f'{sentence} inverted with est-ce')
        return True

    # Weird parataxis misparse:   Hoorde[parataxis] je[nsubj of gekomen] wie er zijn gekomen?
    for tok in sentence:
        if tok.pos_ == 'VERB' and tok.dep_ == 'parataxis' and tok.i < len(sentence) - 1 and sentence[tok.i + 1].dep_ == 'nsubj':
            utils.log(f'{sentence} assumed inverted with weird parataxis misparse')
            return True
        # if tok.pos_ == 'AUX' and tok.dep_ == 'cop' and tok.head.pos_ == 'PRON' and tok.head.dep_ == 'ROOT':   # not sure if good way of dealing with exclamative...
        #     utils.log(f'{sentence} assumed inverted with "(what) is that"-type construction')
        #     return True

    verb, subject = None, None
    finite_verbs = [tok for tok in sentence if tok.pos_ in verblike_pos_tags and 'Fin' in tok.morph.get('VerbForm')]
    for finite_verb in finite_verbs:
        if finite_verb.dep_ in ['acl:relcl', 'ccomp'] or (finite_verb.dep_ == 'aux' and finite_verb.head.dep_ in ['acl:relcl', 'ccomp']):
            # Subordinated clauses
            continue
        if any(tok.dep_ == 'mark' and tok.pos_ == 'SCONJ' and tok.i < finite_verb.i and (tok.head == finite_verb) for tok in sentence):
            # needed to skip "Aangezien je merkte wie je had gezien?"
            continue
        for token in sentence:
            if is_subject_of(token, finite_verb) and 'Rel' not in token.morph.get('PronType'): # or is_subject_of(token, finite_verb.head):
                # Not PronType:Rel both to rule out, e.g., 'Medicijnen die je beter maken?' 'Of vaccines die je beschermen?'
                subject, verb = token, finite_verb
                break
        if verb and subject:
            break

    if verb and subject:
        inversion = verb.i < subject.i
        if subject.lemma_ in vocab.wh_words_all[language] and subject._.is_fronted:
            # Assume there's 'invisible' inversion in case of a fronted wh-subject...
            inversion = True
        utils.log(f'not inverted ({subject}, {verb})' if not inversion else f'inverted ({verb}, {subject})')
        return inversion

    utils.log(f'Subject-verb inversion could not be determined (e.g., subordinate clause, no verb, ...)')
    return None


def is_potential_question_word(token):
    """
    Auxiliary for extract_matrix_question_words, to filter out some definitely-not-question-words
    based on simple language-specific rules (e.g., 'ce qui' in french relatives, never a question word).
    """
    language = utils.language_of(token)
    sentence = token.sent
    if token.text.lower() not in vocab.wh_words[language] + vocab.wh_words_only_embedded[language]:
        return False
    # if token.text.lower() in wh_words_emb[language] and token.dep_ not in ['mark', 'cc']:
    #     ## cc/cconj is a misparse...
    #     return False
    if language == 'dutch':
        if token.i <= 1 and token.text.lower() == 'wat' and len(sentence) > token.i + 1 and sentence[token.i+1].text.lower() == 'een':    # filter out exclamatives (X wat een)
            return False
        # if right_neighbors and right_neighbors[0].text.lower() == 'er':     # Jan weet wie er is gevallen
        #     return True
    if language == 'french':
        if token.i > 2 and sentence[token.i-2].text.lower() == 'à' and sentence[token.i-1].text.lower() == 'ce':  # filter out French free relatives? actually, indirect questions can have this shape.
            return False
        if token.sent.text[:token.idx].strip().lower().endswith('est-ce'):
            # Qu'est-ce que[no] c'est.
            return False
    return True


def is_question_word_for_indirect_only(token):
    language = utils.language_of(token)
    if token.text.lower() in vocab.wh_words_only_embedded[language]:
        utils.log(f'{token} is fit for indirect questions only.')
        return True
    return False


def get_complementizer_of(token):
    sent = token.sent

    if not might_be_complementizer(token):
        return None

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
        utils.log(f'{token} has embedder {sent.root} because advmod/nummod misparse')
        return sent.root

    if token.head.dep_ in ['acl:relcl'] and is_verblike(token.head) and token.head.head.dep_ in ['obj'] and is_embedder(token.head.head.head):
        # Il se demande ce[obj of demande] que[obj of veux] tu veux[acl:relcl of ce] faire.
        utils.log(f'"{token}" has head.head.head "{token.head.head.head}" as embedder (via verblike acl:relcl and obj (like ce))')
        return token.head.head.head
    elif token.head.dep_ in ['obj', 'advcl', 'ccomp', 'acl:relcl'] and is_verblike(token.head) and is_embedder(token.head.head):
        # Wat er precies gebeurde[obj/advcl] heb ik niet kunnen zien/opnemen.
        # Wat hij deed[ccomp] vroeg ik hem[obj] al eerder.
        # Not: Wat hij deed[ccomp] veroorzaakte een ongeluk[obj].
        # Il a lu ce qui lui plait[acl:relcl]?
        utils.log(f'"{token}" has head.head "{token.head.head}" as embedder (via verblike obj/advl/ccomp/acl:relcl)')
        return token.head.head
    elif token.dep_ in ['obj', 'advcl', 'ccomp', 'acl:relcl'] and is_embedder(token.head):
        # TODO Maybe remove 'obj' from this list, for 'Il a vu qui[obj]?'
        # And you know why[ccomp of know]?
        utils.log(f'"{token}" has head "{token.head}" as embedder (as obj/advl/ccomp/acl:relcl/nummod)')
        return token.head
    elif token.dep_ in 'nummod' and is_embedder(token.head.head) and token.head.dep_ == 'parataxis':
        utils.log(f'"{token}" has head "{token.head.head}" as embedder (via nummod of parataxis)')
        return token.head.head
    elif token.head.dep_ == 'ROOT' and not is_embedder(token.head):
        aux = [tok for tok in token.head.children if tok.dep_ == 'aux' and is_embedder(tok)]
        if aux:
            # Misparse: Hoorde[AUX] je wie er zijn gekomen[ROOT]? (with dutch model large only)
            utils.log(f'"{token}" has head "{aux[0]}" as embedder (aux/root misparse)')
            return aux[0]

    for tok in utils.spacy_get_path_to_root(token)[1:]:
        if is_verblike(tok) and is_embedder(tok) and not is_subject_of(token, tok):
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


def might_not_be_complementizer(token):
    if token.dep_ in objectlike_dep_tags and token.head.dep_ != 'ccomp': # and token.head.dep_ == 'ROOT': # + subjectlike_dep_tags?
        # Il a vu qui[obj]?
        utils.log(f'"{token}" might also NOT be a complementizer.')
        return True
    # Aangezien je merkte wie[no] je had gezien[ccomp]?
    utils.log(f'"{token}" cannot NOT be a complementizer.')
    return False


def is_verblike(token):
    # if token.pos_ == 'ADJ' and any(tok.dep_ == 'cop' for tok in token.children):  # cop not needed... Crazy how ...
    #     return True
    return token.pos_ in ['VERB', 'AUX', 'ADJ']


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
    return token.lemma_ in vocab.personal_existentials[language]

def is_impersonal(token):
    language = utils.language_of(token)
    return token.lemma_ in vocab.impersonals[language]

def is_like_who(token):
    language = utils.language_of(token)
    return token.lemma_ in vocab.who_like[language]

def is_negated(token):
    return any(is_negation(tok) for tok in token.children)

def is_negation(token):
    # Beware of discrepancy with regex-based 'has_negation'...
    language = utils.language_of(token)
    if token.dep_ == 'neg' or 'neg' in token.morph.get('Polarity'):
        return True
    if token.lemma_ in vocab.negations[language]:
        return True
    return False

def is_wanted(token):
    return any(tok._.corrected_lemma in vocab.verbs_like_want[utils.language_of(token)] for tok in token.children)


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


def is_embedder(token):
    language = utils.language_of(token)
    lemma = token._.corrected_lemma
    if lemma in vocab.all_embedders[language]:
        utils.log(f'"{token}" is an embedder.')
        return True
    if any(child.dep_ == 'ccomp' for child in token.children):
        utils.log(f'"{token}" is an embedder (ccomp child).')
        return True
    utils.log(f'"{token}" ({lemma}) is not an embedder.')
    return False


def ends_with_tag_question(sentence):
    language = utils.language_of(sentence)
    if language == 'english':
        if [tok.pos_ for tok in sentence[-4:]] == ['AUX', 'PART', 'PRON', 'PUNCT']:
            utils.log(f'Ends as tag question.')
            return True
        elif [tok.pos_ for tok in sentence[-3:]] == ['AUX', 'PRON', 'PUNCT']:
            utils.log(f'Ends as tag question.')
            return True
    if sentence._.ends_with_question_mark and any(sentence.text.strip('?!.').endswith(tag) for tag in vocab.tag_questions[language]):
        utils.log(f'Ends as tag question.')
        return True
    return False


def likely_to_head_indirect_question(token):
    language = utils.language_of(token)
    is_question = token.sent._.ends_with_question_mark and not token.sent._.has_tag_question
    lemma = token._.corrected_lemma
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
        elif not is_question and speaker_subject and (is_negated(token) or is_wanted(token)) and is_present_tense(token):
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
        if not is_question and (speaker_subject or impersonal_subject or not subjects) and is_present_tense(token):
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

    # if lemma in vocab.adjectives_like_strange[language]:
    #     if not is_question and is_present_tense(token):
    #         utils.log(f'Structure resembles: It\'s strange...')
    #         result = True

    if lemma in vocab.verbs_like_ask[language]:
        utils.log(f'Verb "{token}" is like ask.')
        if not is_question and (existential_subject or speaker_subject or impersonal_subject):
            utils.log(f'Structure resembles: Someone asked / I asked / one asks')
            result = True

    if any(tok.pos_ == 'SCONJ' for tok in token.children if tok.i < token.i):
        # Aangezien je merkte... makes indirect question much less likely.
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
    if token.head == verb or (verb.dep_ == 'aux' and token.head == verb.head):
        if token.dep_ in subjectlike_dep_tags:
            # Do[aux of know] you[subj of know] know?
            return True
        if token.dep_ in misparsed_subject_dep_tags and not any(tok.dep_ in subjectlike_dep_tags for tok in token.head.children):
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
    if token.pos_ in ['ADJ', 'PROPN']:
        # PropN for misparse with large dutch model, 'Benieuwd[PropN] hoeveel daarvan zelfmoorden waren'
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
    complementizer_of = get_complementizer_of(token)
    can_be_direct = token.sent._.ends_with_question_mark and not is_question_word_for_indirect_only(token)
    might_not_be_compl = not complementizer_of or might_not_be_complementizer(token)
    if can_be_direct and token._.is_fronted and not might_be_initial_relclause(token) and might_not_be_compl:
        return 'fronted'
    elif complementizer_of:
        if likely_to_head_indirect_question(complementizer_of) and not is_rising_declarative(token.sent):
            return 'indirect'
    if can_be_direct and not might_be_initial_relclause(token) and might_not_be_compl:
        return 'insitu'
    return 'no'


def classify_question(sent):
    fronted = [tok.text for tok in sent if tok._.qtype == 'fronted']
    insitu = [tok.text for tok in sent if tok._.qtype == 'insitu']
    indirect = tuple(tok.text for tok in sent if tok._.qtype == 'indirect')
    if fronted:
        structure = 'wh'
    elif insitu:
        structure = 'insitu'
    elif sent._.has_tag_question:
        structure = 'tag'
    elif sent._.ends_with_question_mark:
        if sent._.has_inversion == False:
            structure = 'risingdecl'
        elif sent._.has_inversion:
            structure = 'polar'
        else:
            structure = 'elliptic'
    else:
        structure = 'decl'
    if indirect:
        use = 'indirect'
    elif structure:
        use = 'direct'
    else:
        use = 'no'
    wh_words_literal = tuple(fronted + insitu)
    wh_words_functional = indirect if indirect else tuple(fronted + insitu)
    return {
        'structure': structure,
        'use': use,
        'wh_words_literal': wh_words_literal,
        'wh_words_functional': wh_words_functional,
    }



def has_negation(text, language=None):
    if not isinstance(text, str): # assume text is a doc
        language = utils.language_of(text)
        text = text.text
    return utils.has_any_keyword(vocab.negations[language], text)


def has_levelers(text, language=None):
    if not isinstance(text, str): # assume text is a doc
        language = utils.language_of(text)
        text = text.text
    return utils.has_any_keyword(vocab.levelers[language], text)


def has_conjunctions(text, language=None):
    if not isinstance(text, str): # assume text is a doc
        language = utils.language_of(text)
        text = text.text
    return utils.has_any_keyword(vocab.conjunctions[language], text)


def has_references_to_other(text, language=None):
    if not isinstance(text, str): # assume text is a doc
        language = utils.language_of(text)
        text = text.text
    return utils.has_any_keyword(vocab.pronouns_other[language], text)


def has_references_to_group(text, language=None):
    if not isinstance(text, str): # assume text is a doc
        language = utils.language_of(text)
        text = text.text
    return utils.has_any_keyword(vocab.pronouns_group[language], text)