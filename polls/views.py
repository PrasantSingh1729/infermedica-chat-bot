from django.http import HttpResponse
from django.shortcuts import render
from .models import Destination
from .models import Chat
from .models import detail
import uuid
import re
#import conversation
from .apiaccess import *
from .constants import *

"""Constants."""

age=0
sex=''
args = {
    "auth": 'b9a8b672:d0e1f233db392a2c7dd34af0eab8ad86',
    "model": '',
    "verbose": '',
}

case_id=''
naming=''
auth_string=''


detail = detail()
dists=[]



#================================================================================================================================


def get_auth_string(auth_or_path):
    if ":" in auth_or_path:
        return auth_or_path
    try:
        with open(auth_or_path) as stream:
            content = stream.read()
            content = content.strip()
            if ":" in content:
                return content
    except FileNotFoundError:
        pass
    raise ValueError(auth_or_path)


def new_case_id():
    return uuid.uuid4().hex



#================================================================================================================================

def form(request):
    return render(request, 'form.html')

def howto(request):
    return render(request, 'howto.html')

def useradd(text):
    dist=Chat()
    print(text)
    dist.by='user'
    dist.text = text
    dists.append(dist)
    print(dists)
    
    

def botadd(text):
    dist=Chat()
    print(text)
    dist.by='bot'
    dist.text = text
    dists.append(dist)
    print(dists)



def index(request):
    dist=Chat()
    dist.by='bot'
    global age
    age = int(request.GET['age'])
    detail.age=age
    global sex
    sex = str(request.GET['sex'])
    detail.sex=sex
    name = str(request.GET['name'])
    detail.name=name
    phn = int(request.GET['number'])
    detail.phnno=phn
    dist.text= f"Hii {name}, What concerns you most about your health? Please describe your symptoms."
    dists.clear()
    global auth_string
    auth_string = get_auth_string('b9a8b672:d0e1f233db392a2c7dd34af0eab8ad86')
    global case_id
    case_id = new_case_id()
    global naming
    naming = get_observation_names(auth_string, case_id, args['model'])
    dists.append(dist)
    print(detail.phnno,detail.name,detail.age,detail.sex)
    return render(request, 'caseid.html',{'dists':dists})


def caseid(request):
    text = str(request.GET['text'])
    useradd(text)
    
    print(naming)
    bottext = str(case_id)
    botadd(bottext)
    return render(request, 'caseid.html',{'dists':dists})



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
    return "Noting: {}".format(", ".join(mention_as_text(m) for m in mentions))




def extract_keywords(text, keywords):
    pattern = r"|".join(r"\b{}\b".format(re.escape(keyword))
                        for keyword in keywords)
    mentions_regex = re.compile(pattern, flags=re.I)
    return mentions_regex.findall(text)

class AmbiguousAnswerException(Exception):
    pass



def extract_decision(text, mapping):

    decision_keywrods = set(extract_keywords(text, mapping.keys()))
    if len(decision_keywrods) == 1:
        return mapping[decision_keywrods.pop().lower()]
    elif len(decision_keywrods) > 1:
        raise AmbiguousAnswerException("The decision seemed ambiguous.")
    else:
        raise ValueError("No decision found.")
diagnoses=''
triage_resp=''
question_struct=''
should_stop_now=''
def question(request):
    global evidence
    global triage_resp
    global diagnoses
    global question_struct
    global should_stop_now
    resp = call_diagnosis(evidence, age, sex, case_id, auth_string,
                                    language_model=None)
    question_struct = resp['question']
    diagnoses = resp['conditions']
    should_stop_now = resp['should_stop']
    if should_stop_now:

        triage_resp = call_triage(evidence, age, sex, case_id,
                                            auth_string,
                                            language_model=None)
        print(evidence,diagnoses,triage_resp)
        # botadd('Here is the result:')

    elif question_struct['type'] == 'single':
        question_items = question_struct['items']
        assert len(question_items) == 1
        question_item = question_items[0]
        question_text=question_struct['text']
        botadd(question_text)


mentions = []
context = []
evidence = [] 
def mention(request):
    text = str(request.GET['text'])
    useradd(text)
    portion=''
    if text=='no':
        portion=None
    global mentions
    global context
    resp = call_parse(text, auth_string, case_id, context, language_model=None)
    portion = resp.get('mentions', [])
    if portion:
        bottext=str(summarise_mentions(portion))+ '. What else would you like to report?'
        botadd(bottext)
        mentions.extend(portion)
        context.extend(context_from_mentions(portion))
        return render(request, 'caseid.html',{'dists':dists})
    # if mentions and portion is None:
    if text=='no' or text=='No':
        global evidence
        evidence = mentions_to_evidence(mentions)
        question(request)
        return render(request, 'interview.html',{'dists':dists})
    botadd('What else would you like to report?')
    return render(request, 'caseid.html',{'dists':dists})



def check(request,text):
    global evidence
    global triage_resp
    global diagnoses
    global question_struct

    new_evidence = []

    if question_struct['type'] == 'single':
        question_items = question_struct['items']
        assert len(question_items) == 1
        question_item = question_items[0]
        # observation_value = read_single_question_answer(
        #     question_text=question_struct['text'])
        try:
            observation_value = extract_decision(text, ANSWER_NORM)
        except (AmbiguousAnswerException, ValueError) as e:
            botadd("{} Please repeat.".format(e))
            return render(request, 'interview.html',{'dists':dists})

        if observation_value is not None:
            new_evidence.extend(question_answer_to_evidence(
                question_item, observation_value))
    else:
        raise NotImplementedError("Group questions not handled in this"
                                    "example")
    evidence.extend(new_evidence)

        # return read_single_question_answer(question_text)

def summarise_diagnoses(diagnoses):
    botadd('Diagnoses:')
    for idx, diag in enumerate(diagnoses):
        botadd('{:2}. {:.2f}% {}'.format(idx + 1, diag['probability']*100,
                                       diag['name']))


def interview(request):
    global evidence
    global triage_resp
    global diagnoses
    text = str(request.GET['text'])
    useradd(text)
    check(request,text)
    question(request)
    if should_stop_now:
        name_evidence(evidence, naming)
        summarise_diagnoses(diagnoses)
        return render(request, 'interview.html',{'dists':dists})
    return render(request, 'interview.html',{'dists':dists})
