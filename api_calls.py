import re
from sqlalchemy import delete
from models import db
import psycopg2
from newsapi import NewsApiClient
from dateutil import parser
from models import QueriedStory, Story, User, QueriedStory, TestQ
newsapi = NewsApiClient(api_key='b4f52eb738354e648912261c010632e7')
# from app import app


def save_to_db(articles, user_id=None):
    """This function saves each article to SQLalchemy DB and returns a list of SQLalchemy story objects to be rendered"""

    # A temporary query is used (user.queried_stories) to keep track of the data from each api call so that we may
    # easily extract this data globally, as well as save space in our own data base by deleting this temporary query
    # each time a new api call occurs.

    if user_id != None:
        user = User.query.get(user_id)
        # deletes all previous instances of queried_stories to make room for new query
        for story in user.queried_stories:
            db.session.delete(story)
            db.session.commit()

        db.session.commit()

    results = []
    for article in articles:
        """This section converts each story from API data to our own SQLalchemy objects"""
        headline = article['title']
        source = article["source"]["name"]
        if article["content"] is None:
            # sometimes Newsapi is unable to provide content for each story
            content = "No content preview found. Click the link above to access the full story."
        else:
            content = article['content']

        author = article['author']
        description = article['description']
        url = article['url']
        image = article['urlToImage']
        api_date = article['publishedAt']
        published_at = parser.parse(api_date)
        story = Story(headline=headline, source=source, content=content,
                      author=author, description=description, url=url, image=image,
                      published_at=published_at)
        results.append(story)
        db.session.add(story)
        db.session.commit()

        if user_id != None:
            user = User.query.get(user_id)
            user.queried_stories.append(story)
            db.session.commit()

    return results


def api_call(query=None, user_id=None):
    # queries = TestQ.query.all()
    # query = TestQ.pop()
    # if query.type == "detailed_search":
    #     results = advanced_search_call(query, user_id)
    #     return results
    # elif query.type == "simply_search":
    #     results = simple_search_call(query)
    #     return results
    # elif query.type == "headlines":
    #     results = top_headlines_call(query)
    #     return results
    # else:
    #     if query.type == "category":
    #         results = cat_calls(query.type)
    #         return results
    """Makes API call for top headlines"""
    if query == None:
        # in the context of this function, we determine that a request for headlines is being made if there is no search query given
        if user_id != None:
            results = top_headlines_call(query, user_id)
        else:
            results = top_headlines_call(query)
        return results

    """Makes API call for simple search from search bar in navbar (keyword only)"""
    if type(query) == str:
        # in the context of this function, we determine the type of search being made by the argument passed being a string of the keyword entered in the navbar
        if user_id != None:
            results = simple_search_call(query, user_id)
        else:
            results = simple_search_call(query)
        return results

    """Makes API call for advanced search"""
    # in the context of this function, we determine that an advanced search call is being made if it hasn't been flagged as a simple search or headline call

    if user_id != None:
        user = User.query.get(user_id)
        results = advanced_search_call(query, user_id)
    else:
        results = advanced_search_call(query)
    return results


"""Individual functions for separate types of API Calls"""


def cat_calls(query):
    data = newsapi.get_top_headlines(language="en", category=f"{query}")
    articles = data['articles']
    saved = save_to_db(articles)
    return saved


def simple_search_call(query, user_id=None):
    data = newsapi.get_everything(q=f"{query}")
    articles = data['articles']
    if user_id != None:
        saved = save_to_db(articles, user_id)
    else:
        saved = save_to_db(articles)
        return saved


def top_headlines_call(user_id=None):
    data = newsapi.get_top_headlines(language="en")
    articles = data['articles']
    saved = save_to_db(articles)
    return saved


def advanced_search_call(query, user_id=None):
    from_ = str(query['date_from'])
    to = str(query['date_to'])
    print("source1", query['source'])

    # check if this is necessary
    if to == 'None' and from_ == 'None':
        data = newsapi.get_everything(q=f"{query['keyword']}", sources=f"{query['source']}", language=f"{query['language']}", sort_by=f"{query['sort_by']}"
                                      )

    elif to == 'None' and from_ != 'None':
        data = newsapi.get_everything(q=f"{query['keyword']}", sources=f"{query['source']}", language=f"{query['language']}", sort_by=f"{query['sort_by']}", from_param=f"{from_}"
                                      )

    elif to != 'None' and from_ == 'None':

        data = newsapi.get_everything(q=f"{query['keyword']}", sources=f"{query['source']}", language=f"{query['language']}", sort_by=f"{query['sort_by']}", to=f"{to}"
                                      )

    else:
        data = newsapi.get_everything(q=f"{query['keyword']}", sources=f"{query['source']}", language=f"{query['language']}", sort_by=f"{query['sort_by']}", from_param=f"{from_}", to=f"{to}"
                                      )
    # api seems to not want to allow dates to be optional if specified

    # I ran into trouble with the pagesize parameter from news-api, however a
    # temporary solution to this is to extract that number from the query dict,
    # and then splice the resulting list of articles.
    quantity = int(query['quantity'])
    articles = data['articles']
    spliced = articles[:quantity]
    if user_id != None:
        saved = save_to_db(spliced, user_id)
    else:
        saved = save_to_db(spliced)
    return saved
