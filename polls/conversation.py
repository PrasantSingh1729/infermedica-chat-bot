import re
import sys
from .apiaccess import *
from .constants import *


class AmbiguousAnswerException(Exception):
    pass


# def read_input(prompt):
#     if prompt.endswith('?'):
#         prompt = prompt + ' '
#     else:
#         prompt = prompt + ': '
#     print(prompt, end='', flush=True)
#     return sys.stdin.readline().strip()



def read_complaint_portion(auth_string, case_id, context, language_model=None):

    text = input('Describe you complaints')
    if not text:
        return None
    resp = call_parse(text, auth_string, case_id, context, language_model=language_model)

    return resp.get('mentions', [])


def mention_as_text(mention):
    _modality_symbol = {"present": "+", "absent": "-", "unknown": "?"}
    name = mention["name"]
    symbol = _modality_symbol[mention["choice_id"]]
    return "{}{}".format(symbol, name)


def context_from_mentions(mentions):
    """Returns IDs of medical concepts that are present."""
    return [m['id'] for m in mentions if m['choice_id'] == 'present']


def summarise_mentions(mentions):
    """Prints noted mentions."""
    print("Noting: {}".format(", ".join(mention_as_text(m) for m in mentions)))


def read_complaints(auth_string, case_id, language_model=None):

    mentions = []
    context = []
    while True:
        portion = read_complaint_portion(auth_string, case_id, context, language_model=language_model)
        if portion:
            summarise_mentions(portion)
            mentions.extend(portion)
            context.extend(context_from_mentions(portion))
        if mentions and portion is None:
            # User said there's nothing more but we've already got at least one
            # complaint.
            return mentions


def read_single_question_answer(question_text):
    answer = input(question_text)
    if not answer:
        return None

    try:
        return extract_decision(answer, ANSWER_NORM)
    except (AmbiguousAnswerException, ValueError) as e:
        print("{} Please repeat.".format(e))
        return read_single_question_answer(question_text)


def conduct_interview(evidence, age, sex, case_id, auth, language_model=None):
    while True:
        resp = call_diagnosis(evidence, age, sex, case_id, auth,
                                        language_model=language_model)
        question_struct = resp['question']
        diagnoses = resp['conditions']
        should_stop_now = resp['should_stop']
        if should_stop_now:

            triage_resp = call_triage(evidence, age, sex, case_id,
                                                auth,
                                                language_model=language_model)
            return evidence, diagnoses, triage_resp
        new_evidence = []
        if question_struct['type'] == 'single':
            question_items = question_struct['items']
            assert len(question_items) == 1
            question_item = question_items[0]
            observation_value = read_single_question_answer(
                question_text=question_struct['text'])
            if observation_value is not None:
                new_evidence.extend(question_answer_to_evidence(
                    question_item, observation_value))
        else:
            raise NotImplementedError("Group questions not handled in this"
                                      "example")
        evidence.extend(new_evidence)


def summarise_some_evidence(evidence, header):
    print(header + ':')
    for idx, piece in enumerate(evidence):
        print('{:2}. {}'.format(idx + 1, mention_as_text(piece)))
    print()


def summarise_all_evidence(evidence):
    reported = []
    answered = []
    for piece in evidence:
        (reported if piece.get('initial') else answered).append(piece)
    summarise_some_evidence(reported, 'Patient complaints')
    summarise_some_evidence(answered, 'Patient answers')


def summarise_diagnoses(diagnoses):
    print('Diagnoses:')
    for idx, diag in enumerate(diagnoses):
        print('{:2}. {:.2f} {}'.format(idx + 1, diag['probability'],
                                       diag['name']))
    print()


def summarise_triage(triage_resp):
    print('Triage level: {}'.format(triage_resp['triage_level']))
    teleconsultation_applicable = triage_resp.get(
        'teleconsultation_applicable')
    if teleconsultation_applicable is not None:
        print('Teleconsultation applicable: {}'
              .format(teleconsultation_applicable))
    print()


def extract_keywords(text, keywords):
    """Extracts keywords from text.

    Args:
        text (str): Text from which the keywords will be extracted.
        keywords (list): Keywords to look for.

    Returns:
        list: All keywords found in text.

    """
    # Construct an alternative regex pattern for each keyword (speeds up the
    # search). Note that keywords must me escaped as they could potentialy
    # contain regex-specific symbols, e.g. ?, *.
    pattern = r"|".join(r"\b{}\b".format(re.escape(keyword))
                        for keyword in keywords)
    mentions_regex = re.compile(pattern, flags=re.I)
    return mentions_regex.findall(text)


def extract_decision(text, mapping):

    decision_keywrods = set(extract_keywords(text, mapping.keys()))
    if len(decision_keywrods) == 1:
        return mapping[decision_keywrods.pop().lower()]
    elif len(decision_keywrods) > 1:
        raise AmbiguousAnswerException("The decision seemed ambiguous.")
    else:
        raise ValueError("No decision found.")


def extract_sex(text, mapping):
    """Extracts sex keywords from text.

    Args:
        text (str): Text from which the keywords will be extracted.
        mapping (dict): Mapping from keyword to sex.

    Returns:
        str: Single decision (one of `mapping` values).

    Raises:
        AmbiguousAnswerException: If `text` contains keywords mapping to two
            or more different distinct sexes.
        ValueError: If no keywords can be found in `text`.

    """
    sex_keywords = set(extract_keywords(text, mapping.keys()))
    if len(sex_keywords) == 1:
        return mapping[sex_keywords.pop().lower()]
    elif len(sex_keywords) > 1:
        raise AmbiguousAnswerException("I understood multiple sexes.")
    else:
        raise ValueError("No sex found.")


def extract_age(text):
    """Extracts age from text.

    Args:
        text (str): Text from which the keywords will be extracted.

    Returns:
        str: Found number (as a string).

    Raises:
        AmbiguousAnswerException: If `text` contains two or more numbers.
        ValueError: If no numbers can be found in `text`.

    """
    ages = set(re.findall(r"\b\d+\b", text))
    if len(ages) == 1:
        return ages.pop()
    elif len(ages) > 1:
        raise AmbiguousAnswerException("I understood multiple ages.")
    else:
        raise ValueError("No age found.")
