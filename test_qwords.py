import ling
import utils
import re


def main():

    with open('data/testing/qwords.txt', 'r') as file:
        current_language = None
        for line in file:
            if not line.strip():
                continue
            if line.startswith('#'):
                content = line.strip('# \n').lower()
                if content in ['dutch', 'english', 'french', 'italian']:
                    current_language = content
                if content == 'stop':
                    break
                continue

            sentence = line.split('#')[0].strip()
            if '|' in sentence:
                sentence, structure = sentence.split('|')
                sentence = sentence.strip()
                structure = structure.strip()
            else:
                structure = None
            sentence_untagged, token_start_to_tag = process_tags(sentence)
            utils.VERBOSE = False
            parsed_sentence = utils.spacy_single(sentence_untagged, current_language)
            utils.VERBOSE = True
            error = False
            for token in parsed_sentence:
                tag = token_start_to_tag.get(token.idx, 'no')
                if token._.qtype != tag:
                    if not error:
                        print('>>>', sentence)
                    print('ERROR (q-word): Predicted:', token._.qtype, ' | True:', tag)
                    error = True
            if structure and parsed_sentence._.qtype['structure'] != structure:
                if not error:
                    print('>>>', sentence)
                print(f'ERROR (structure): Predicted:', parsed_sentence._.qtype['structure'], ' | True:', structure)
                error = True
            if error:
                utils.spacy_single(sentence_untagged, current_language)
                utils.print_parse(parsed_sentence)
                print('-------------------')


def process_tags(tagged_sentence):
    """
    Wie[fronted] eet jij op?  -->  Wie eet jij op?, {0: 'fronted'}
    """
    token_start_to_tag = {}
    char_offset = 0
    for match in re.finditer(r"\b([\w']+)(\[(\w+)])", tagged_sentence):
        token_start, token_end = match.span(1)
        tag_start, tag_end = match.span(2)
        tag = match.group(3)
        token_start_to_tag[token_start + char_offset] = tag
        char_offset -= tag_end - tag_start
    sentence_untagged = re.sub(r'\[\w+]', '', tagged_sentence)

    return sentence_untagged, token_start_to_tag


if __name__ == '__main__':
    main()