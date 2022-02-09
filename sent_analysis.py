#libraries for parsing and sentiment analysis
from bs4 import BeautifulSoup
from newspaper import Article
from sqlalchemy.exc import IntegrityError
import nltk
nltk.download('stopwords')
nltk.download('punkt')
from nltk.corpus import stopwords
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
sia = SIA()
from textblob import TextBlob

import spacy
nlp = spacy.load('en_core_web_sm', disable=["parser", "ner"])
import re



def parse(headline):
    article = Article(headline.url)
    article.download()
    article.parse()
    parsed = article.text
    return parsed

def tokenize(headline):
    parsed = parse(headline)
    #tokenization from spacy and remove punctuations, convert to set to remove duplicates
    words = set([str(token) for token in nlp(parsed) if not token.is_punct])
    print("Below is length upon tokenization")
    print(len(words))
    # remove digits and other symbols except "@"--used to remove email
    words = list(words)
    words = [re.sub(r"[^A-Za-z@]", "", word) for word in words]
     #remove special characters
    words = [re.sub(r'\W+', '', word) for word in words]
    #remove websites and email addresses 
    words = [re.sub(r'\S+@\S+', "", word) for word in words]
    #remove empty spaces 
    words = [word for word in words if word!=""]
    
    print("Below is length before stopwords")
    print(len(words))
    #import lists of stopwords from NLTK
    stop_words = set(stopwords.words('english'))
    words = [w for w in words if not w.lower() in stop_words]

    print("Below is length after stopwords filtered")
    print(len(words))

    # lemmization from spacy. doesn't appear to be doing anything. fix this
    words = [token.lemma_ for token in nlp(str(words)) if not token.is_punct]
    print("Below is length after Lemmatization")
    print(len(words))

    vowels = ['a','e','i','o','u']
    words = [word for word in words if any(v in word for v in vowels)]
    print("Below is length after words with no vowels removed")
    print(len(words))  
    
    #eliminate duplicate words by turning list into a set
    words_set = set(words)
    print("Below is length after converted to set")
    print(len(words_set)) 

    return words_set
    # sources: https://towardsdatascience.com/a-step-by-step-tutorial-for-conducting-sentiment-analysis-a7190a444366
    #https://datascience.stackexchange.com/questions/39960/remove-special-character-in-a-list-or-string

def subjectize(headline):
    parsed = parse(headline)
    tblobbed = TextBlob(parsed)
    subjectivity = tblobbed.sentiment.subjectivity
    sub_obj = {}
    if subjectivity > .80:
        sub_obj['measure'] = "Very Objective"
    elif subjectivity > .60:
        sub_obj['measure'] = "Moderately Objective"
    elif subjectivity > .40:
        sub_obj['measure'] = "Neutral"
    elif subjectivity > .20:
        sub_obj['measure'] = "Moderately Subjective"
    else:
        sub_obj['measure'] = "Very Subjective"
    sub_obj['score'] = subjectivity
    return sub_obj

def polarize(headline):
    #function returns an object of two sepearate polarity scores; one based off the text of the article and the other
    #from just the headline alone. Each of these are represented in their own respective objects. 
    pol_obj = {}
    headline_res = {}
    article_res = {}

    """Logic for polarity from article text"""
    parsed = parse(headline)
    sentenced = nltk.tokenize.sent_tokenize(parsed)

    coms = []
    pos = []
    negs = []
    neus = []

    for sentence in sentenced:
        res = sia.polarity_scores(sentence)

        pos.append(res["pos"])
        negs.append(res["neg"])
        neus.append(res["neu"])
        if res['compound']:
            #sometimes the composite will be zero for certain sentences. We don't want to include that data. 
            coms.append(res['compound'])

    avg_com = sum(coms) / len(coms)
    avg_pos = sum(pos) / len(pos)
    avg_neu = sum(neus) / len(neus)
    avg_neg = sum(negs) / len(negs)

    """Logic for polarity from headline text"""

    headline = sia.polarity_scores(headline.headline)
    headline_res["com"] = headline['compound']
    headline_res["pos"] = headline['pos']
    headline_res["neg"] = headline['neg']
    headline_res["neu"] = headline['neu']

    if headline_res['com'] >= 0.2 :
        headline_res['result'] = "Positive"
 
    elif headline_res['com'] <= - 0.2 :
        headline_res['result'] = "Negative"
 
    else:
        headline_res['result'] = "Neutral"

    article_res["avg_com"] = avg_com
    article_res["avg_pos"] = avg_pos
    article_res["avg_neg"] = avg_neg
    article_res["avg_neu"] = avg_neu

    if avg_com >= 0.2 :
        article_res['result'] = "Positive"
 
    elif avg_com <= - 0.2 :
        article_res['result'] = "Negative"
 
    else :
        article_res['result'] = "Neutral"

    print(f"Average sentiment of each sentence in article: compound {avg_com}")
    print(f"sentence was rated as , {avg_neg *100}, % Negative")
    print(f"sentence was rated as , {avg_neu *100}, % Neutral")
    print(f"sentence was rated as , {avg_pos *100}, % Positive")

    pol_obj['headline_res'] = headline_res
    pol_obj['article_res'] = article_res
    return pol_obj

def sa_sum(headlines):
    for headline in headlines:
        sum = {}
        sum['parsed']  = parse(headline)
        sum['tokenized'] = tokenize(headline)
        sum['subjectivity'] = subjectize(headline)
        sum['polarity'] = polarize(headline)
    return sum