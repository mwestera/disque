import ling
import utils
import re

# test_file_path = 'data/testing/qwords.txt'
# test_file_path = 'data/testing/qwords_dutch.txt'
test_file_path = 'data/testing/qwords_french.txt'

def main():

    n_errors = 0

    with open(test_file_path, 'r') as file:
        current_language = None
        for line in file:
            if not line.strip():
                continue
            if line.startswith('//'):
                content = line.strip('/ \n').lower()
                if content in ['dutch', 'english', 'french', 'italian']:
                    current_language = content
                if content == 'stop':
                    break
                continue

            if '//' in line:
                sentence, comment = line.split('//')
                comment = comment.strip()
            else:
                sentence, comment = line, None

            sentence = sentence.strip()
            sentence = utils.clean_question(sentence)   # TODO Remember this for the main pipeline!

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
                tag = token_start_to_tag.get(token.idx, None)
                if token._.qtype != tag:
                    if not error:
                        print('>>>', line)
                    print('ERROR (q-word): Predicted:', token._.qtype, ' | True:', tag)
                    error = True
                    n_errors += 1
            if structure and parsed_sentence._.qtype['structure'] != structure:
                if not error:
                    print('>>>', line)
                print(f'ERROR (structure): Predicted:', parsed_sentence._.qtype['structure'], ' | True:', structure)
                error = True
                n_errors += 1
            if error:
                utils.spacy_single(sentence_untagged, current_language)
                utils.print_parse(parsed_sentence)
                print('-------------------')

    print(f'Found {n_errors} errors.')

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