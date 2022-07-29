# libraries for parsing and sentiment analysis
import nltk
from textblob import TextBlob
import spacy
import re
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
from nltk.corpus import stopwords
from newspaper import Article
from multiprocessing.dummy import Pool as ThreadPool


nltk.download('vader_lexicon')
nltk.download('stopwords')
nltk.download('punkt')
sia = SIA()


nlp = spacy.load('en_core_web_sm', disable=["parser", "ner"])


def parse(headline, text_only=False):
    dict = {'id': headline['session_id'],
            'headline': headline.headline}
    try:
        article = Article(headline.url)
        article.download()
        article.parse()
        parsed = article.text
        if text_only:
            return parsed
        dict['text'] = parsed
        return dict
    except:
        return ""


def parse_async(headlines):
    pool = ThreadPool(10)
    results = pool.map(parse, headlines)
    pool.close()
    pool.join()
    return results


def tokenize(headline):
    parsed = parse(headline)
    # tokenization from spacy and remove punctuations, convert to set to remove duplicates
    words = set([str(token) for token in nlp(parsed) if not token.is_punct])
    print("Below is length upon tokenization")
    print(len(words))
    # remove digits and other symbols except "@"--used to remove email
    words = list(words)
    words = [re.sub(r"[^A-Za-z@]", "", word) for word in words]
    # remove special characters
    words = [re.sub(r'\W+', '', word) for word in words]
    # remove websites and email addresses
    words = [re.sub(r'\S+@\S+', "", word) for word in words]
    # remove empty spaces
    words = [word for word in words if word != ""]

    print("Below is length before stopwords")
    print(len(words))
    # import lists of stopwords from NLTK
    stop_words = set(stopwords.words('english'))
    words = [w for w in words if not w.lower() in stop_words]

    print("Below is length after stopwords filtered")
    print(len(words))

    # lemmization from spacy. doesn't appear to be doing anything. fix this
    words = [token.lemma_ for token in nlp(str(words)) if not token.is_punct]
    print("Below is length after Lemmatization")
    print(len(words))

    vowels = ['a', 'e', 'i', 'o', 'u']
    words = [word for word in words if any(v in word for v in vowels)]
    print("Below is length after words with no vowels removed")
    print(len(words))

    # eliminate duplicate words by turning list into a set
    words_set = set(words)
    print("Below is length after converted to set")
    print(len(words_set))

    return words_set
    # sources: https://towardsdatascience.com/a-step-by-step-tutorial-for-conducting-sentiment-analysis-a7190a444366
    # https://datascience.stackexchange.com/questions/39960/remove-special-character-in-a-list-or-string


def subjectize(headline, parsed=False):
    try:
        if parsed:
            parsed = headline['text']
        else:
            parsed = parse(headline, text_only=True)
    except:
        return None
    tblobbed = TextBlob(parsed)
    # separate this logic out into separate function
    subjectivity = round(tblobbed.sentiment.subjectivity, 2)
    subjectivity = str(subjectivity)
    subjectivity = subjectivity[-2:]
    if subjectivity == ".":
        subjectivity = f"{subjectivity}0"
    if subjectivity == ".0":
        return None
    subjectivity = round(float(subjectivity))

    sub_obj = {}
    if subjectivity > 80:
        sub_obj['measure'] = f"{subjectivity}% (Very Objective)"
    elif subjectivity > 60:
        sub_obj['measure'] = f"{subjectivity}% (Objective)"
    elif subjectivity > 40:
        sub_obj['measure'] = f"{subjectivity}% (Neutral)"
    elif subjectivity > 20:
        sub_obj['measure'] = f"{subjectivity}% (Subjective)"
    else:
        sub_obj['measure'] = f"{subjectivity}% (Very Subjective)"
    sub_obj['score'] = subjectivity

    if sub_obj['score'] == 0.0:
        return None
    return sub_obj


def polarize(headline, parsed=False):
    # function returns an object of two sepearate polarity scores; one based off the text of the article and the other
    # from just the headline alone. Each of these are represented in their own respective objects.
    pol_obj = {}
    headline_res = {}
    article_res = {}

    """Extracting polarity from article text"""
    try:
        """First argument might be a dictionary that's already been parsed and turned into a dictionary
        to be used in order_pol() by async_parse (in the case of multiple articles). Alternatively, it could
        be a single sqlalchemy object of a news story that needs to be parsed. In the latter case, we just 
        want text, as we don't need to keep track of ids."""

        # first argument is a dictionary
        if parsed:
            parsed = headline
            sentenced = nltk.tokenize.sent_tokenize(parsed['text'])
            headline = sia.polarity_scores(parsed['headline'])

        # first argument is a sqlalchemy object
        else:
            parsed = parse(headline, text_only=True)
            sentenced = nltk.tokenize.sent_tokenize(parsed)
            headline = sia.polarity_scores(headline.headline)

    except:
        return None

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
            # sometimes the composite will be zero for certain sentences. We don't want to include that data.
            coms.append(res['compound'])

    if len(coms) == 0:
        return None
    avg_com = round((sum(coms) / len(coms)), 2)
    avg_pos = round((sum(pos) / len(pos)), 2)
    avg_neu = round((sum(neus) / len(neus)), 2)
    avg_neg = round((sum(negs) / len(negs)), 2)

    article_res["avg_com"] = round(avg_com, 2)
    article_res["avg_pos"] = round(avg_pos, 2)
    article_res["avg_neg"] = round(avg_neg, 2)
    article_res["avg_neu"] = round(avg_neu, 2)

    if avg_com >= 0.4:
        article_res['result'] = f"{avg_com} (Very Positive)"

    elif avg_com >= 0.2:
        article_res['result'] = f"{avg_com} (Positive)"

    elif avg_com <= - 0.2:
        article_res['result'] = f"{avg_com} (Negative)"

    elif avg_com <= - 0.2:
        article_res['result'] = f"{avg_com} (Very Negative)"

    else:
        article_res['result'] = f"{avg_com} (Neutral)"

    article_res["message"] = f"{article_res['result']}. {avg_neg *100}% Negative, {avg_neu *100}% Neutral, and {avg_pos *100}% Positive"
    """Extracting polarity from headline text"""

    headline_res["com"] = headline['compound']
    headline_res["pos"] = headline['pos']
    headline_res["neg"] = headline['neg']
    headline_res["neu"] = headline['neu']

    if headline_res['com'] >= 0.2:
        headline_res['result'] = "Positive"

    elif headline_res['com'] >= 0.4:
        headline_res['result'] = "Very Positive"
    elif headline_res['com'] <= - 0.2:
        headline_res['result'] = "Negative"
    elif headline_res['com'] <= - 0.4:
        headline_res['result'] = "Very Negative"

    else:
        headline_res['result'] = "Neutral"

    pol_obj['headline_res'] = headline_res
    pol_obj['article_res'] = article_res
    return pol_obj
