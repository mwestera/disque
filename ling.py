import re
import utils
import vocab

# sentence_separators = '?!.…'
# sentence_pattern = r'((?!\s\s[A-Z])[^.!?\"\'():;\n\t…])+[?!.…]+'

def extract_potential_questions(text, language):
    for sentence in utils.quick_sentencize(text, language):
        start = sentence[0].idx
        sentence = sentence.text
        if sentence.strip('!').endswith('?') or utils.has_any_keyword(vocab.wh_words_all[language], sentence):
            yield sentence, start
    # for match in re.finditer(sentence_pattern, text):
    #     sentence = match.group()
    #     span = match.span()
    #     if sentence.strip('!').endswith('?') or utils.has_any_keyword(vocab.wh_words_all[language], sentence):
    #         yield sentence, span

verblike_pos_tags = ['AUX', 'VERB']
objectlike_dep_tags = ['dobj', 'obj', 'iobj', 'obl', 'obl:agent', 'obl:arg']
subjectlike_dep_tags = ['nsubj', 'nsubjpass', 'nsubj:pass', 'csubj', 'csubjpass', 'expl', 'expl:subj']
misparsed_subject_dep_tags = ['nmod:poss', 'obj']
ccomplike_dep_tags = ['acl:relcl', 'ccomp']

def ends_with_question_mark(sent):
    return sent.text.strip('!').endswith('?')


def is_fronted(token):
    matrix_verb = token.sent._.matrix_verb
    if matrix_verb:
        if token.head.dep_ == 'conj' and (token.head.head == matrix_verb or matrix_verb in token.head.head.children) and any(tok.pos_ == 'CCONJ' and tok.dep_ == 'cc' for tok in token.head.children if matrix_verb.i < tok.i < token.i):
            if any(tok._.qtype == 'fronted' for tok in token.sent if tok.i < token.i):
                # ” wanneer[fronted] ben je geïnfecteerd en wanneer[fronted] ben je besmet? | wh
                return True
            else:
                return False
            # TODO Maybe consider parataxis here too?
        else:
            return token.i < matrix_verb.i
    if any(tok.dep_ in ['ccomp'] for tok in utils.spacy_get_path_to_root(token)[1:]):
        # exception; if using all ccomplike_dep_tags instead, it gets wrong for "Als ik een onderbroek koop...etc".
        return False
    if token.head.dep_ in ['acl:relcl'] and token.head.head.i < token.i and token.head.head.pos_ in verblike_pos_tags:
        # The latter for weird misparse: Beste  , waar kan ik informatie vinden over beker indeling jeugd b categorie en wat indeling is van de jo7-12?
        return False
    return True


def is_rising_declarative(sentence):
    if sentence._.ends_with_question_mark and not sentence._.has_inversion:
        utils.log('Sentence seems like a rising declarative.')
        return True
    return False


def get_finite_verbs_of_span(span):
    if not span:
        return []
    language = utils.language_of(span[0])
    result = []
    for tok in span:
        if any(child.pos_ in verblike_pos_tags and child.dep_ in ['aux', 'cop'] and 'Fin' in child.morph.get('VerbForm') and child.i < tok.i for child in tok.children):
            # sometimes infinitives are misparsed; also check for aux/cop to avoid hitting parataxis misparses.
            continue
        if tok.pos_ in verblike_pos_tags and 'Fin' in tok.morph.get('VerbForm'):
            result.append(tok)
        if language == 'dutch' and tok.dep_ == 'ROOT' and tok.pos_ == 'VERB' and tok.text.startswith('be') and tok.text.endswith('d'):
            # bedoeld typo...
            result.append(tok)
    return result


def determine_matrix_subject_and_verb(sentence):
    if sentence.root.dep_ != 'ROOT':
        # weird misparse
        sentence._.matrix_verb = None
        sentence._.matrix_subject = None
        return sentence

    language = utils.language_of(sentence[0])

    verb, subject = None, None
    punctuation = [tok for tok in sentence[1:-1] if tok.pos_ == 'PUNCT' and tok.text == ',']
    if punctuation and (sentence[0].pos_ == 'SCONJ' or sentence[1].pos_ == 'SCONJ'):
        spans = [sentence.doc[:punctuation[0].i], sentence.doc[punctuation[0].i:]]
        # for start, end in zip(punctuation, punctuation[1:]):
        #     spans.append(sentence[start.i:end.i])
        # if len(punctuation) > 1:
        #     spans.append(sentence[punctuation[-1].i:])
        finite_verbs = []
        for span in spans[::-1]:
            finite_verbs.extend(get_finite_verbs_of_span(span))
    else:
        finite_verbs = get_finite_verbs_of_span(sentence)

    for finite_verb in finite_verbs:
        if finite_verb.dep_ == 'parataxis' and finite_verb.head.dep_ == 'ROOT' and 'Fin' in finite_verb.head.morph.get('VerbForm') and finite_verb.head.i - finite_verb.i < 3:
            # misparse:  Nee ma[parataxis] ik[nsubj] zie[root] mensen gewoon halloweenfeestjes geven alsof corona gedaan is?
            # Weet[parataxis] iemand misschien hoe[indirect] lang er na een vastgestelde besmetting delen van het Corona virus in je lichaam blijven zitten en je dus positief blijft testen (Ook als je niet meer besmettelijk bent)? | polar
            continue
        if finite_verb.dep_ in ccomplike_dep_tags or (finite_verb.dep_ in ['aux', 'aux:tense'] and finite_verb.head.dep_ in ccomplike_dep_tags):
            # Subordinated clauses; now better dealt with by kinda splitting on punctuation
            continue
        if any(tok.dep_ == 'mark' and tok.pos_ == 'SCONJ' and (tok.head.head == finite_verb or finite_verb in tok.head.children) for tok in sentence.doc[:finite_verb.i]):
            # needed to skip "Aangezien je merkte wie je had gezien?" (elliptic; otherwise predicted to be rising decl)
            # vs. - Als[SCONJ, mark of kan] het veilig kan waarom niet ?
            continue
        candidate_subject = get_subject_of(finite_verb)
        if candidate_subject:
            if not verb:
                verb = finite_verb
                subject = candidate_subject
            elif ((finite_verb.dep_ == 'conj' and not any(child.dep_ == 'cc' for child in finite_verb.children)) or
                  (finite_verb.head.dep_ == 'conj' and not any(child.dep_ == 'cc' for child in finite_verb.head.children))):
                # Overwrite already selected verb only if this one is conjoined to the right, without an explicit conjunction?
                verb = finite_verb
                subject = candidate_subject
        if language in ['french'] and not candidate_subject and finite_verb.text.lower() in vocab.french_il_drop_verbs:
            verb = finite_verb
    # if not verb and finite_verbs: # No longer needed it seems...
    #     # topmost finite verb by default...
    #     verb = finite_verbs[0]  # use the first finite verb to determine fronting? wrong for    Als het veilig kan waarom[fronted] niet ?
    #     subject = get_subject_of(verb)    # wrong result for: Aangezien je merkte wie je had gezien?
    utils.log(f'Determined matrix subject {subject} and verb {verb}.')
    sentence._.matrix_verb = verb
    sentence._.matrix_subject = subject
    return sentence


def get_subject_of(verb):
    language = utils.language_of(verb)
    candidates = verb.sent
    # if language == 'french' and verb.i + 1 < len(verb.sent):
    #     # for french. prioritize subsequent pronouns as in est-ce (misparsed in "1000 pers positives/j est ce 1 vague de décès covid ?"); for small model.
    #     candidates = candidates # [verb.sent[verb.i + 1], *candidates]
    subject = None
    for token in candidates:
        if is_subject_of(token, verb) and 'Rel' not in token.morph.get('PronType'):  # or is_subject_of(token, finite_verb.head):
            # Not PronType:Rel both to rule out, e.g., 'Medicijnen die je beter maken?' 'Of vaccines die je beschermen?'
            if not subject:
                subject = token
            elif language == 'french' and token.i == verb.i + 1 and (token.text == 'ce' or (token.pos_ == 'PRON' and token.text.startswith('-'))): # and subject.pos_ != 'PRON':
                # for french.prioritize subsequent pronouns as in est-ce (misparsed in "1000 pers positives/j est ce 1 vague de décès covid ?")
                # Also mind:  Nous[PRON, obj] aurait-on menti ?
                subject = token
                break
            else:
                break
    return subject


def has_subj_verb_inversion(sentence):
    """
    Checks if root verb comes before subject, or check for 'est-ce' in French, and with special clause for
    copula + ADJ constructions, where the dependency parser treats the ADJ as the sentence root.
    """
    language = utils.language_of(sentence)
    if language == 'french' and 'est-ce' in sentence.text.lower()[:20]:
        utils.log(f'{sentence} inverted with est-ce')
        return True

    # if tok.pos_ == 'AUX' and tok.dep_ == 'cop' and tok.head.pos_ == 'PRON' and tok.head.dep_ == 'ROOT':   # not sure if good way of dealing with exclamative...
    #     utils.log(f'{sentence} assumed inverted with "(what) is that"-type construction')
    #     return True

    verb = sentence._.matrix_verb
    subject = sentence._.matrix_subject
    if verb and subject:

        inversion = verb.i < subject.i
        if subject.lemma_ in vocab.wh_words_all[language]:
            # Assume there's 'invisible' inversion in case of a wh-subject...
            inversion = True
        if inversion and language == 'dutch':
            # in Dutch, inversion after advmod doesn't count: e.g., "Eigenlijk blijven de meeste winkels dus open?"
            if any(tok.i < verb.i and tok.dep_ == 'advmod' for tok in verb.children):
                inversion = False
        if any(tok.dep_ == 'mark' and tok.pos_ == 'SCONJ' and tok.head == verb for tok in sentence.doc[:verb.i]):
            # subordinate clause, e.g., aangezien je merkte wie je had gezien
            utils.log(f'Subject-verb inversion could not be determined (subordinate clause)')
            return None

        utils.log(f'not inverted ({subject}, {verb})' if not inversion else f'inverted ({verb}, {subject})')
        return inversion

    utils.log(f'Subject-verb inversion could not be determined (e.g., no verb, ...)')
    return None


def is_potential_question_word(token):
    language = utils.language_of(token)
    if token.text.lower() not in vocab.wh_words[language] + vocab.wh_words_only_embedded[language]:
        return False
    return True


def simply_not_a_question_word(token):
    language = utils.language_of(token)
    sentence = token.sent
    # if token.text.lower() in wh_words_emb[language] and token.dep_ not in ['mark', 'cc']:
    #     ## cc/cconj is a misparse...
    #     return False
    if language == 'dutch':
        if token.i <= sentence.start + 1 and token.text.lower() == 'wat' and len(sentence) + sentence.start > token.i + 1 and sentence.doc[token.i+1].text.lower() == 'een':    # filter out exclamatives (X wat een)
            return True
        # if right_neighbors and right_neighbors[0].text.lower() == 'er':     # Jan weet wie er is gevallen
        #     return True
        if (token.pos_ == 'DET' or token.dep_ == 'det') and token.i < len(sentence) + sentence.start - 1 and token.doc[token.i + 1].pos_ == 'NOUN' and 'Plur' in token.doc[token.i + 1].morph.get('Number'):
            # Wil nog snel wat kleren en speelgoed gaan kopen.
            return True
        if token.text == 'waar' and token.pos_ == 'ADJ' and any(tok.dep_ == 'cop' for tok in token.children):
            # Dit kan niet waar zijn toch?
            return True
    if language == 'french':
        if token.i > 2 + sentence.start and token.doc[token.i-2].text.lower() == 'à' and token.doc[token.i-1].text.lower() == 'ce':
            # filter out French free relatives? actually, indirect questions can have this shape too.
            return True
        preceding = token.doc[sentence.start:token.i].text.strip().lower()
        if preceding.endswith('est -ce') or preceding.endswith('est ce'):
            # Qu'est-ce que[no] c'est.
            return True
        if token.text == 'ou' and token.pos_ == 'CCONJ' and token.dep_ == 'cc':
            # vous la voulez pile ou face?
            return True
        if token.text.lower() == 'que' and token.head.dep_ == 'dep' and not any(tok.pos_ in verblike_pos_tags for tok in token.head.children):
            # nominal-only comparatives: Les hommes seraient-ils moins intelligents que[no] les animaux ? | polar
            # could include verbal too, but seems risky.
            return True
        # if token.head.dep_ == 'acl:relcl' and token.head.head.lemma_ == 'celui':
        #     return True
        phrase = sentence.doc[token.i:].text.strip().lower()
        if phrase.startswith('quand même') or phrase.startswith('quand bien même'): # or phrase.startswith('quand meme')
            # Si[no] j’ai le Covid, je peux quand[no] même le donner non ???   // quand même / quand bien même = toch, toch wel
            return True
    return False


def is_question_word_for_indirect_only(token):
    language = utils.language_of(token)
    if token.text.lower() in vocab.wh_words_only_embedded[language]:
        utils.log(f'{token} is fit for indirect questions only.')
        return True
    return False


def get_embedder_of(token):
    sent = token.sent
    candidate = None

    actual_roots_given_parataxis_misparse = [tok for tok in sent.doc[:token.i] if tok.pos_ == 'VERB' and tok.dep_ in ['nsubj', 'parataxis']]
    if actual_roots_given_parataxis_misparse and is_embedder(actual_roots_given_parataxis_misparse[0]):
        utils.log(f'{token} has embedder {actual_roots_given_parataxis_misparse[0]} because weird parataxis/nsubj misparse')
        # Hoorde [VERB, parataxis] je wie er zijn gekomen?
        # Weet [VERB, nsubj] Jan wie er zijn gekomen?
        # Il te [VERB, nsubj of dira] le dira quand ton frère?  --> still returns the wrong root though.
        return actual_roots_given_parataxis_misparse[0]

    if token.dep_ == 'advmod' and token.head == sent.root and is_embedder(sent.root) and sent.root.i < token.i: # and any(parataxa_or_ccomp)
        # Fixes some misparses:
        #   Il a dit pourquoi (advmod of dit) il l'a fait?
        #   weet (ROOT) je waarom (advmod of weet) jan sliep (parataxis)?
        #   Il a demandé quand[advmod of demandé]
        utils.log(f'{token} possibly has embedder {sent.root} because advmod/nummod misparse')
        candidate = sent.root
    elif token.head.dep_ in ['acl:relcl'] and is_verblike(token.head) and token.head.head.dep_ in ['obj'] and is_embedder(token.head.head.head):
        # Il se demande ce[obj of demande] que[obj of veux] tu veux[acl:relcl of ce] faire.
        utils.log(f'"{token}" possibly has head.head.head "{token.head.head.head}" as embedder (via verblike acl:relcl and obj (like ce))')
        candidate = token.head.head.head
    elif token.head.dep_ in ['obj', 'advcl'] + ccomplike_dep_tags and is_verblike(token.head) and is_embedder(token.head.head):
        # Wat er precies gebeurde[obj/advcl] heb ik niet kunnen zien/opnemen.
        # Wat hij deed[ccomp] vroeg ik hem[obj] al eerder.
        # Not: Wat hij deed[ccomp] veroorzaakte een ongeluk[obj].
        # Il a lu ce qui lui plait[acl:relcl]?
        utils.log(f'"{token}" possibly has head.head "{token.head.head}" as embedder (via verblike obj/advl/ccomp/acl:relcl)')
        candidate = token.head.head
    elif token.dep_ in ['obj', 'advcl'] + ccomplike_dep_tags and is_embedder(token.head) and not token.head.dep_ in ccomplike_dep_tags:
        # TODO Maybe remove 'obj' from this list, for 'Il a vu qui[obj]?'
        # And you know why[ccomp of know]?
        # Last addition for: Y’a un truc que[no] je comprends[acl:relcl] pas.
        utils.log(f'"{token}" possibly has head "{token.head}" as embedder (as obj/advl/ccomp/acl:relcl/nummod)')
        candidate = token.head
    elif token.dep_ in 'nummod' and is_embedder(token.head.head) and token.head.dep_ == 'parataxis':
        utils.log(f'"{token}" possibly has head "{token.head.head}" as embedder (via nummod of parataxis)')
        candidate = token.head.head
    elif token.head.dep_ == 'ROOT' and not is_embedder(token.head):
        aux = [tok for tok in token.head.children if tok.dep_ in ['aux', 'aux:tense'] and is_embedder(tok)]
        if aux:
            # Misparse: Hoorde[AUX] je wie er zijn gekomen[ROOT]? (with dutch model large only)
            utils.log(f'"{token}" possibly has head "{aux[0]}" as embedder (aux/root misparse)')
            candidate = aux[0]

    if candidate and might_be_complementizer(token, candidate):
        return candidate

    for tok in utils.spacy_get_path_to_root(token)[1:]:
        if is_verblike(tok) and not is_subject_of(token, tok) and is_embedder(tok) and not (token.head == tok and token.dep_ == 'mark') and not tok.dep_ in ccomplike_dep_tags:
            if might_be_complementizer(token, tok):
                utils.log(f'{token} has nearest verblike embedding ancestor {tok} as embedder')
                return tok
            break
        if tok.dep_ == 'obl':
            embedding_nouns = [child for child in tok.head.children if child.dep_ in objectlike_dep_tags and child.pos_ == 'NOUN' and is_embedder(child)]
            if embedding_nouns:
                utils.log(f'{token} has nearest embedding noun {embedding_nouns[0]} as embedder')
                return embedding_nouns[0]
        if tok.dep_ == 'nmod' and is_embedder(tok.head):
            utils.log(f'{token} has nearest embedding noun {tok.head} as embedder')
            return tok.head
    # child of obl of search (with information as object)
    # nmod of information

    utils.log(f'{token} has no embedder')
    return None


def might_be_complementizer(token, embedder):
    language = utils.language_of(token)
    if any(tok.lemma_ in vocab.neutral_pronouns[language] and tok.dep_ in objectlike_dep_tags for tok in embedder.children if tok != token):
        utils.log(f'"{token}" is not complementizer of {embedder}, because there\'s already an impersonal pronoun as obj')
        # Il te le [pron, obj of dira] dira quand ton frère? (even though misparsed)
        return False
    if token.dep_ == 'mark' and token.head.head == embedder:
        utils.log(f'"{token}" might be complementizer of {embedder}, itself the mark of embedder\'s child.')
        return True
    if any(grandchild.dep_ == 'mark' and grandchild.lemma_ in vocab.complementizers[language] and grandchild != token for child in embedder.children for grandchild in child.children):
        utils.log(f'"{token}" is not complementizer of {embedder}, because the latter has another mark as grandchild')
        return False
    if any(child.dep_ == 'mark' and child.lemma_ in vocab.complementizers[language] and child != token for child in embedder.children):
        utils.log(f'"{token}" is not complementizer of {embedder}, because the latter has another mark as child')
        return False
    # if token.dep_ in objectlike_dep_tags and token.head == embedder:  # Too strict; replaced by preceding rule.
    #     utils.log(f'"{token}" is not complementizer of {embedder}, because it\'s simply the obj.')
    #     return False
    if token.dep_ == 'cc' and token.pos_ == 'CCONJ' and any(tok._.qtype == 'indirect' and might_be_complementizer(tok, embedder) for tok in token.sent[:token.i]):
        # >>> Ik vraag mij nog steeds af waarom[indirect] mensen nu 2 verschillende spuiten of[no] nog iets toegevoegd bij de griepprik kregen.
        utils.log(f'"{token}" is not complementizer of {embedder}, because it\'s more likely a conjunction (of something embedded).')
        return False
    if token.dep_ == 'cc' and token.pos_ == 'CCONJ' and token.head.dep_ == 'conj':
        utils.log(f'"{token}" is not complementizer of {embedder}, because it\'s part of a conjunction.')
        return False
    if token.pos_ == 'CCONJ' and token.dep_ == 'fixed':
        utils.log(f'"{token}" is not complementizer of {embedder}, because it\'s part of a conjunction (dep=fixed).')
        return False
    if token.dep_ == 'xcomp' and token.i == token.sent.start:
        # for misparse, though insufficient to handle it correctly: Hoe[fronted] ziet u een "zegevierplan"?
        utils.log(f'"{token}" is not complementizer of {embedder}, because it is initial and parsed as xcomp (?).')
        return False
    if token.dep_ == 'advmod' and token.i == token.sent.start and token.i == token.head.i - 1 and any(tok.dep_ in objectlike_dep_tags for tok in token.head.children):
        # Waar zie jij jezelf over 5 of 10 jaar?
        utils.log(f'"{token}" is not complementizer of {embedder}, because it seems like a simple fronted advmod.')
        return False
    utils.log(f'"{token}" might be complementizer of {embedder}, as there is no alternative mark or impersonal pronoun as obj.')
    return True


def might_not_be_complementizer(token):
    if token.dep_ in objectlike_dep_tags and token.head.dep_ != 'ccomp': # and token.head.dep_ == 'ROOT': # + subjectlike_dep_tags?
        # Il a vu qui[obj]?
        utils.log(f'"{token}" might also NOT be a complementizer.')
        return True
    if token.dep_ == 'xcomp' and token.i == token.sent.start:
        # for misparse, though insufficient to handle it correctly: Hoe[fronted] ziet u een "zegevierplan"?
        utils.log(f'"{token}" might also NOT be a complementizer.')
        return False
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
    verbs_like_want = vocab.verbs_like_want[utils.language_of(token)]
    if token.dep_ == 'xcomp' and token.head.dep_ == 'ROOT' and 'Inf' in token.head.morph.get('VerbForm') and token.head._.corrected_lemma in verbs_like_want:
        # for misparse: Ik zou wel eens willen[ROOT] weten[xcomp] wat er allemaal wel goed gaat
        return True
    return any(tok._.corrected_lemma in verbs_like_want for tok in token.children)


def corrected_lemma(token):
    lemma = token.lemma_.lower()

    if lemma in ['vragen', 'vraag']:
        compound_parts = [tok for tok in token.children if tok.dep_ == 'compound:prt']
        if any(compound_parts):
            lemma = compound_parts[0].lemma_ + '_' + lemma
    if lemma == 'merkken':
        lemma = 'merken'
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
    sentence_text = re.sub(r'^[^\w]+|[^\w]+$', '', sentence.text)
    if language == 'french' and sentence_text.endswith(' ou non'):
        return not sentence._.has_inversion # if so, ou non is polar-like altQ.
    if sentence._.ends_with_question_mark and any(sentence_text.endswith(tag) for tag in vocab.tag_questions[language]):
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
        elif not is_question and speaker_subject and (is_negated(token) and is_present_tense(token)) or is_wanted(token):
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
        if not is_question and is_present_tense(token) and 'Plur' not in token.morph.get('Number'):
            utils.log(f'Structure resembles: It\'s a mystery...')
            result = True

    if lemma in vocab.nouns_like_information[language]:
        if is_present_tense(token):
            utils.log(f'Structure resembles: ...information about...')
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
    language = utils.language_of(token)
    if verb.dep_ == 'parataxis' and token.i == verb.i + 1 and token.dep_ in subjectlike_dep_tags:
        # weird parataxis misparse  Hoorde[parataxis] je[nsubj of gekomen] wie er zijn gekomen?
        return True
    if token.pos_ == 'NOUN' and 'Plur' in token.morph.get('Number') and token.dep_ == 'advmod' and token.head.dep_ == 'ROOT' and token.i == token.head.i - 1 and 'Plur' in token.head.morph.get('Number'):
        # bare plural subject misparse:   Vliegtuigmaatschappijen[advmod] weten natuurlijk niet op voorhand hoeveel reizigers zij gaan vervoeren die dag.
        return True
    if token.head == verb or (verb.dep_ in ['aux', 'aux:tense', 'aux:pass'] and token.head == verb.head):
        if token.dep_ in subjectlike_dep_tags:
            # Do[aux of know] you[subj of know] know?
            return True
        if token.dep_ in misparsed_subject_dep_tags and not any(tok.dep_ in subjectlike_dep_tags for tok in token.head.children):
            # common misparse, e.g., "Weet iemand[OBJ] of het vaccin veilig is?"
            return True
    if verb.dep_ == 'cop' and token == verb.head and verb.morph.get('Number') == token.morph.get('Number'):
        # E.g., Is[cop] er Covid19[ROOT]?
        return True
    if verb.dep_ == 'cop' and token.head == verb.head and token.dep_ in subjectlike_dep_tags:
        # E.g., Of ben[cop] jij[nsubj] niet kritisch genoeg?
        return True
    # if token.dep_ in subjectlike_dep_tags and verb.head.head == token.head and verb.dep_ == 'cop':
    #     # for misparse with nl_lg only: U bent duidelijk iemand die niet wil begrijpen hoe zorgwekkend de huidige toestand is.
    #     return True
    if language == 'french':
        if token.pos_ == 'PRON' and token.text.startswith('-') or token.text == 'ce':
            if token.i == verb.i+2 and token.doc[token.i+1].text.startswith('-'):
                return True
            elif token.i == verb.i+1:
                # E.g., sauront-ils[subj of repondre] y repondre?
                return True
        if token.pos_ == 'PRON' and token.dep_ == 'ROOT' and verb.dep_ == 'dep' and verb.head == token:
            return True
        if verb.i == token.sent.start and token.i == token.sent.start + 1 and token.pos_ == 'PRON' and verb.head == token.head:
            # misparse:  Êtes[aux, punct of diplome] vous[pron, aux:pass of diplome] diplômé de médecine ?
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
    # TODO Could be more sophisticated...
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

def is_noun_like(token):
    if token.head.head.pos_ == 'NOUN':
        return True
    if token.head.head.pos_ == 'ADJ' and token.head.head.i > token.sent.start + 1 and token.doc[token.head.head.i - 1].pos_ == 'DET':
        # prix à  payer pour protéger les vieux[adj] qui sont vaccinés?
        return True
    return False


def might_be_ordinary_relclause(token):
    """
    >>> might_be_ordinary_relclause(utils.spacy_single('Wat hij deed was stom.', 'dutch')[0])
    True
    >>> might_be_ordinary_relclause(utils.spacy_single('Wat hij deed veroorzaakte een ongeluk.', 'dutch')[0])
    True
    >>> might_be_ordinary_relclause(utils.spacy_single('Ik vond wat hij deed niet leuk.', 'dutch')[2])
    True
    >>> might_be_ordinary_relclause(utils.spacy_single('Ik weet niet wat hij deed.', 'dutch')[3])
    False
    >>> might_be_ordinary_relclause(utils.spacy_single('Wat deed hij dan?', 'dutch')[0])
    False
    >>> might_be_ordinary_relclause(utils.spacy_single('Weet je wat hij deed?', 'dutch')[2])
    False
    >>> might_be_ordinary_relclause(utils.spacy_single('Wat was het dat hij deed?', 'dutch')[0])
    False
    >>> might_be_ordinary_relclause(utils.spacy_single('Wat dacht je dat hij zei?', 'dutch')[0])
    False
    >>> might_be_ordinary_relclause(utils.spacy_single('Wat er precies gebeurde heb ik niet kunnen zien.', 'dutch')[0])
    False
    >>> might_be_ordinary_relclause(utils.spacy_single('Wat er precies gebeurde heb ik niet kunnen opnemen.', 'dutch')[0])
    True
    >>> might_be_ordinary_relclause(utils.spacy_single('Wat er gebeurde was een wonder.', 'dutch')[0])
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
    if token.dep_ == 'advmod' and token.head.dep_ == 'acl:relcl' and token.head.head.pos_ == 'NOUN':
        return True
    if token.dep_ in subjectlike_dep_tags + objectlike_dep_tags and token.head.dep_ == 'acl:relcl' and is_noun_like(token):
        return True
    if token.head.dep_ in ['csubj', 'nsubj']:
        # Wat hij deed[csubj] veroorzaakte[ROOT] een storm.
        # Wat er gebeurde[nsubj] was een wonder[ROOT].
        return True
    if token.head.dep_ == 'acl:relcl' and token.head.head.pos_ == 'NOUN' and token.i - 1 == token.head.head.i:
        # Un vaccin qui donne quoi Ã  long terme ?
        return True
    if token.dep_ == 'mark' and token.head.dep_ == 'advcl':
        # Et pourquoi pas leur couper les vivre pendant qu[mark of advcl of couper]'on y est ?
        return True
    if token.dep_ == 'mark' and token.i > token.sent.start and token.doc[token.i-1].dep_ == 'mark' and token.head == token.doc[token.i-1].head:
        # Et pourquoi pas leur couper les vivre pendant[mark] qu[mark]'on y est ?
        return True
    language = utils.language_of(token)
    if language == 'dutch':
        if token.lemma_ == 'wat' and token.i < token.sent.start + len(token.sent) - 1 and token.doc[token.i+1].lemma_ == 'er':
            # pretty good rule!
            return True

    return False


def is_exclamative_like(sentence):
    if sentence.text.endswith('!'):
        utils.log('Sentence is more like an exclamative.')
        return True
    return False


def classify_whword(token):
    if not is_potential_question_word(token):
        return None
    if simply_not_a_question_word(token):
        utils.log(f'{token} is simply not a question word.')
        return 'no'
    embedder_of = get_embedder_of(token)
    can_be_direct = token.sent._.ends_with_question_mark and not is_question_word_for_indirect_only(token)
    might_not_be_compl = not embedder_of or might_not_be_complementizer(token)
    if can_be_direct and is_fronted(token) and not might_be_ordinary_relclause(token) and might_not_be_compl:
        return 'fronted'
    elif embedder_of:
        if likely_to_head_indirect_question(embedder_of) and not is_exclamative_like(token.sent):   # and not is_rising_declarative(token.sent)    commented out for "waar kan ik informatie vinden over .. en wat...", seems ok.
            return 'indirect'
    if can_be_direct and not might_be_ordinary_relclause(token) and might_not_be_compl:
        return 'insitu'
    return 'no'


def classify_question(sent):
    fronted = [tok.text.lower() for tok in sent if tok._.qtype == 'fronted']
    insitu = [tok.text.lower() for tok in sent if tok._.qtype == 'insitu']
    indirect = tuple(tok.text.lower() for tok in sent if tok._.qtype == 'indirect')
    if sent._.has_tag_question and not fronted + insitu:
        # only if no wh word:  pourquoi non?
        structure = 'tag'
    elif fronted:
        structure = 'wh'
    elif insitu:
        structure = 'insitu'
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
    elif structure != 'decl':
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