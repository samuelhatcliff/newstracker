#general imports
import os
from newsapi.newsapi_client import NewsApiClient
from dateutil import parser
from models import db, Story, User
# newsApi imports
from newsapi.newsapi_client import NewsApiClient
import creds
my_api_key = os.environ.get("API_KEY", creds.api_key)
newsapi = NewsApiClient(api_key=my_api_key)
#async imports
from multiprocessing.dummy import Pool as ThreadPool



def save_to_db(articles, user_id=None):
    """This function saves each article to SQLalchemy DB and returns a list of SQLalchemy story objects to be rendered"""

    # A temporary query is used (user.queried_stories) to keep track of the data from each api call so that we may
    # easily extract this data globally.

    if user_id:
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
        if not article["content"]:
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

        if user_id:
            user = User.query.get(user_id)
            user.queried_stories.append(story)
            db.session.commit()

    return results


def api_call(query=None, user_id=None):
    """Makes API call for top headlines"""
    if not query:
        # in the context of this function, we determine that a request for headlines is being made if there is no search query given
        if user_id:
            results = top_headlines_call(query, user_id)
        else:
            results = top_headlines_call(query)
        return results

    """Makes API call for simple search from search bar in navbar (keyword only)"""
    if type(query) == str:
        # if this function is called via simple_search view function, the query will be a string
        if user_id:
            results = simple_search_call(query, user_id)
        else:
            results = simple_search_call(query)
        return results

    """Makes API call for advanced search"""
    # in the context of this function, we determine that an advanced search call is being made if it hasn't been flagged as a simple search or headline call

    results = advanced_search_call(query, user_id)
    return results


"""Individual functions for separate types of API Calls"""
def async_reqs(query):
    pool = ThreadPool(10)
    results = pool.map(cat_calls, query)
    #we only use this function with cat_calls, as the latter is the only function where we need to send separate requests to the api
    #at the same time
    pool.close()
    pool.join()
    return results

def cat_calls(query):
    """Gets generalized headlines for a specific catagory"""
    data = newsapi.get_top_headlines(language="en", category=f"{query}")
    articles = data['articles']
    saved = save_to_db(articles)
    return saved


def simple_search_call(query, user_id=None):
    """Gets results from simple search """
    data = newsapi.get_everything(q=f"{query}")
    articles = data['articles']
    if user_id:
        saved = save_to_db(articles, user_id)
    else:
        saved = save_to_db(articles)
        return saved


def top_headlines_call(user_id=None):
    """Gets Generic top headlines"""
    data = newsapi.get_top_headlines(language="en")
    articles = data['articles']
    if user_id:
        saved = save_to_db(articles, user_id)
        return saved
    saved = save_to_db(articles)
    return saved


def advanced_search_call(query, user_id=None):
    from_ = str(query['date_from'])
    to = str(query['date_to'])
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

    if user_id:
        saved = save_to_db(spliced, user_id)
    else:
        saved = save_to_db(spliced)
    return saved
