from newsapi import NewsApiClient
from flask import session, Flask
from app import session 
from dateutil import parser
from models import Story, User
newsapi= NewsApiClient(api_key='b4f52eb738354e648912261c010632e7')
import psycopg2
from models import db
# from app import app



def get_from_newsapi(query):
    if query != None:
        articles = query
    else:
        print("didnt get nuttin1")
        data = newsapi.get_top_headlines(language="en")
        articles = data['articles']
    
    print(articles)
    print('articles1')
    print("poop")
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

    return top_headlines

def get_search_results(query):
    from_ = str(query['date_from'])
    to = str(query['date_to'])
    print("555")
    print(type(to))
    print("date5")
    results = newsapi.get_everything(q=f"{query['keyword']}"
    ,sources = f"{query['source']}"
    ,language=f"{query['language']}"
    ,sort_by=f"{query['sort_by']}"
    ,from_param=f"{from_}"
    ,to=f"{to}"
    )
    
    
                                      
                                    #   to=f'{query.date_to}',
                                
                                    # #   sort_by=f'{query.sort_by}'
                                    #   page_size= f'{query.quantity}'
                                                                          #   search_in = f"{query['search_in']}")

                                      #searchIn and pageSize may be incorrect due to casing
    #having trouble with the pageSize search parameter which represents # of stories to be returned
    #temporary solution to this is to extract that number from the query dict, and then splice the resulting
    #list of articles. 
    print("success")
    quantity = int(query['quantity'])
    articles = results['articles']
    spliced = articles[:quantity]
    return spliced