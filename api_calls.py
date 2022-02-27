from newsapi import NewsApiClient
from dateutil import parser
from models import QueriedStory, Story, User, QueriedStory
newsapi= NewsApiClient(api_key='b4f52eb738354e648912261c010632e7')
import psycopg2
from models import db
from sqlalchemy import delete
import re;
# from app import app



def get_from_newsapi(query, user_id = None):
    # if user_id == None:
    #     #catch error
    #     return None
    user = User.query.get(user_id)

    if user_id != None:
                #deletes all previous instances of queried_stories to make room for new query

        for story in user.queried_stories:
            db.session.delete(story)
            db.session.commit()
            
        db.session.commit()
      

    if query != None:
        articles = query
    else:
        data = newsapi.get_top_headlines(language="en")
        articles = data['articles']
    
    top_headlines = []
    for article in articles:
        headline = article['title']
        source = article["source"]["name"]
        if article["content"] is None:
            content = "No content preview found. Click the link above to access the full story."
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

        if user_id != None:
            user.queried_stories.append(story)
            db.session.commit()
            
    

    return top_headlines

def search_call(query, user_id):
    
    from_ = str(query['date_from'])
    to = str(query['date_to'])
   
    #check if this is necessary
    if to == 'None' and from_ == 'None':
        
        results = newsapi.get_everything(q=f"{query['keyword']}"
        ,sources = f"{query['source']}"
        ,language=f"{query['language']}"
        ,sort_by=f"{query['sort_by']}"
        )

    elif to == 'None' and from_ != 'None':
       
        results = newsapi.get_everything(q=f"{query['keyword']}"
        ,sources = f"{query['source']}"
        ,language=f"{query['language']}"
        ,sort_by=f"{query['sort_by']}"
        ,from_param=f"{from_}"
        )
  
        

    elif to != 'None' and from_ == 'None':
   
        results = newsapi.get_everything(q=f"{query['keyword']}"
        ,sources = f"{query['source']}"
        ,language=f"{query['language']}"
        ,sort_by=f"{query['sort_by']}"
        ,to=f"{to}"
        )

    else:
        print('correct')
        results = newsapi.get_everything(q=f"{query['keyword']}"
        ,sources = f"{query['source']}"
        ,language=f"{query['language']}"
        ,sort_by=f"{query['sort_by']}"
        ,from_param=f"{from_}"
        ,to=f"{to}"
        )
    print("nah")
    #api seems to not want to allow dates to be optional if specified
  
    #having trouble with the pageSize search parameter which represents # of stories to be returned
    #temporary solution to this is to extract that number from the query dict, and then splice the resulting
    #list of articles. 
    quantity = int(query['quantity'])
    articles = results['articles']
    spliced = articles[:quantity]
    saved = get_from_newsapi(spliced, user_id )
    print(saved)
    print("saved1")
    return saved