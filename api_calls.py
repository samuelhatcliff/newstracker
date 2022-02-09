from newsapi import NewsApiClient
from flask import session
from dateutil import parser
from models import Story
newsapi= NewsApiClient(api_key='b4f52eb738354e648912261c010632e7')


def get_from_newsapi():
    if session['query']:
        data = get_search_results(session['query'])
    else:
        data = newsapi.get_top_headlines(language="en")
    articles = data['articles']
    top_headlines = []
    for article in articles:
        headline = article['title']
        source = article["source"]["name"]
        if type(article["content"]) == None:
            print("ITS A NONE TYPE")
            content = "Click the following link to view story."
        else:
            content=article['content']
        
        author =article['author']
        description = article['description']
        url = article['url']
        image = article['urlToImage']
        api_date = article['publishedAt']
        published_at = parser.parse(api_date)
        views = 0
        story = Story(headline=headline, source=source, content=content,
        author=author, description=description, url=url, image=image,
        published_at= published_at, views=views)
        top_headlines.append(story)
        db.session.add(story)
        db.session.commit()
        del session['query']

    return top_headlines

def get_search_results(query):
    results = newsapi.get_everything(q=f'{query.keyword}',
                                      search_in = f'{query.search_in}',
                                      sources=f'{query.source}',
                                      from_param=f'{query.date_from}',
                                      to=f'{query.date_to}',
                                      language=f'{query.language}',
                                      sort_by=f'{query.sort_by}',
                                      page_size= f'{query.quantity}')
                                      #searchIn and pageSize may be incorrect due to casing
    
    return results