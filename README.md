# newstracker

## Technology/Tools: 
Python, Flask, SQLAlchemy, Redis, NewsAPI, NLTK, Newspaper, Axios, WTForms, CSS, Bootstrap,


## Summary: 
  NewsTracker is an application designed to enhance and optimize the way a user interacts with news stories. 
  This is achieved primarily using a search engine that connects to [NewsAPI](https://newsapi.org/) which allows the user to narrow-down the content of their results.  
  Additional search parameters such as [Polarity](https://www.nltk.org/api/nltk.sentiment.html) and [Subjectivity](https://www.topcoder.com/thrive/articles/getting-started-with-textblob-for-sentiment-analysis#:~:text=Subjectivity%20is%20the%20output%20that,%2C%20WordNet%20integration%2C%20and%20more.) use Natural Language Processing through Python's [NLTK](https://www.nltk.org/) and [Textblob](https://textblob.readthedocs.io/en/dev/) libararies to parse through 
  the html data given by the URL returned by NewsAPI, which will order a user's search results by the degree to which an article is objective or positive, 
 with the corresponding score listed for each article.
  
  Other features available to users include the ability to save stories that they want to refer back to later, save multiple search queries for easy-access through an accordian drop-down, and the ability to set one of said queries as a user's default so that their headline feed will be base its results off that query
  default so that the main headline page will show results based off of the user's default search query. 

## Purpose: 
  The ability to run an advanced search query to display a specific type of story and store it permanently in a user's account could be beneficial for 
  anyone wanting to keep up with current events and/or investment opportunities. Getting Sentimental Analysis prior to reading a story has a variety of potential 
  benefits. Imagine the following scenarios:

    1) An investor is trying to assess the pros and cons of owning stock in a particular company. Using the
    subjectivity feature to identify degrees of subjectivity, they may choose to filter out articles that are
    marked as highly subjective, which allows them to save researching time and become better informed.

    2) Someone wanting to become more politically informed about a particular issue may use the subjectivity 
    feature to identify news sources and types of stories that may not be worth reading due to the degree to
    which the author's tone skews from being objective. 

    3) A day/swing trader may want to use the polarity feature to evaluate the overall market sentiment of a
    particular stock, crypto, or geo-political region. 

    4) An individual has been feeling that the amount of negative news they've been consuming has taken a toll
    on their mental health, and want to expose themselves to more positive and uplifting news may use the polarity 
    feature to filter out negative stories. 

  As you can see, there are many potential use-cases for NewsTracker that will only continue to increase as more features are added. I would note, however, 
  that NLTK's Sentimental Analysis features are not perfect, and a user should not expect to get accurate results or insights 100% of the time. 


## User-Flow: 
  The homepage of NewsTracker contains an easily accessible Demo User login button on the top right of the page, which allows a visitor to access the same feautures as a real user. The page as a whole contains cards on the left side explaining various features of the app,
  while the right side contains multiple Bootstrap carousels
  containing the top headlines for each category permitted to us by the News Api.  Clicking on each story as they pass through the carousel results 
  in said story opening up in a new window, while clicking the category name itself returns a feed of headlines containing the stories displayed in the carousel.  
  
  ![Homepage](static/photos/user_flows/homepage-mobile.png)
  
  A user can use the links in the navbar to log-in or register. After which, they will be redirected to a feed of headlines (*referred to as "Headlines" in the navbar*)
  or a feed displaying results from their default search query, if previously selected. 
  
  Now that a user is logged in, they may want to user features of the application only available to users, such as the Advanced Search feature (*"Detailed Search" in 
  the navbar*) or refer to previous saved stories (*"My Stories" in the navbar*).
  
  Along with the option of filtering one's search results by polarity or subjectivity, a user may choose to get such sentimental analysis data on any individual stories
  wherever they are rendered, with the exception of the category-carousels on the home-page. 
 
## Data: 
### Postgresql/Flask-SqlAlchemy

  News Tracker uses a Postgresql database configured through Flask-Sqlalchemy on the backend to store information that we want to persist in our application regardless of the client. When reduced to the absolute minimum amount necessary for the application to work as envisioned, we are left only with information pertaining to a registered user. This is composed of information given by a user upon registration, as well as stories and search queries that they may have saved. In SQL terms, we are left with a simple schema containing 3 tables: `User`, `Story`, and `Query`, where `Story` and `Query` are associated with their respective user by a foreign key in a one-way, one-to-many relationsip.
A diagram of our Postgresql schema is shown below. 
  
  ![Schema](static/photos/db-schema.png)
  
### Flask's Server-Side Session with Redis
  Data that doesn't need to persist, in our case being regular search queries and search results that a user does not choose to save, are temporarily stored memory with Flask's Server-Side Session configured through a Redis database. By taking the approach of avoiding using our Postgresql database except when absolutely necessary, we reduce latency and increase overall permformance. A more in depth explanation discussing the trade-offs of using Posgresql, Server Side Session, and Client Side Session for this project can be found here. Below is a basic diagram of how Session is used to temporarily store data.
  
 ![Session-Diagram](static/photos/session-diagram.png)

  ### News-Api
  
Data for individual news stories is sent to Newstracker by either one of the two endpoints NewsApi provides; `Get Top Headlines`, and `Get Everything`. `Get Everything` is the more customizable endpoint, with a sizable amount of different parameters, many of which are utilized in News-Tracker's advanced search. `Get Top Headlines`, on the other hand, only allows language and category as its parameters. Both are used at various points throughout the app. The diagram below illustrates the directional flow of information and data as it travels throughout the application.
  
It's helpful to conceptualize these two endpoints as such that requests generated by user input call the `Get Everything` endpoint (essentially all 'searches') whereas all api requests simply wanting to get the top stories for everything or by category will call the `Get Top Headlines` endpoint. 

Thus, the overall flow of news story data can be concieved of as `NewsApi Results ---> Session Storage ---> Postgresql`, being one-directional and capable of stopping at each point without arriving at the next. An simple illustration representing this process is shown below.

![All-Data-Simplefied](static/photos/all-data-simplified.png)

### Summary
Now that we've walked through each step in News Tracker's dataflow, let's combine everything we've covered into a single diagram which gives us a more precise understanding of how data might be accessed throughout the application. While not comprehensive, the following diagram now includes specific routes, instances of API calls, our Sentimental Analysis logic, and Jinja templates.

![Diagram](static/photos/newstracker-data-v1.drawio.png)

After extracting the resulting data from the api, the data is saved to Flasks's Server-Side Session, configured using a Redis database. This allows the results returned from the most recent request accessible globally within the app, and for each story to be assigned a unique data using Python's uuid(). This id is inherited as the primary key the story's Sqlalchemy object if it ends up getting saved by a user to our database. 




## Challenges: 
### Limitations NewsApi's 'Free' Tier
#### Problem: Inability to access a story's full content.
  The free version of news API does not allow developers to access the entirety of a story's content, only providing the first few sentences. This is a huge problem for our app, since one of the key features we've imagined is to perform sentimental analysis on the body of each article, not just the headline or a few sentences! 
  
#### My Solution: Webscape from URL 
  Although we peasants don't have access to the article's body through NewsApi's free tier, we *are* given the URL, through which we can access an article's body by sending an HTTP request to the url and extracting the full content from the HTML, otherwise known as web-scraping. The only problem (and it's a big one) is that a web-scraper needs to know where it can expect to find the content to extract (ei, a div with an id of x) which would be an extremely difficult task given that we are dealing with dozens of news sources, each with their own uniquely structured html layouts. This is where the `Newspaper` Library comes in. [Newspaper](https://newspaper.readthedocs.io/en/latest/) sends a request to a given url and is able to parse the actual content of the article, regardless of the source, with surprising accuracy, rarely including "junk" content such as ads, comments, etc. Frankly, I don't have much of an idea how the underlying mechanics of this library works. Although not 100% perfect, it performs accurately enough for the purpose of this app, and is our magical little solution to address this issue of dynamic webscraping. 
  
#### Problem: Multiple consecutive HTTP requests for each story drastically increases user wait time. 
But wait! Now that we've decided that we're going to retrieve a story's full content by webscraping each URL, we've introduced a new problem. Each time we want to access full content from a single news story, we have to wait for a full "Request-Response" cycle to be completed. Just a single one can sometimes take several seconds! How are we going to provide an enjoyable user experience if a user is forced to wait between 10-30 seconds or more each time they want to search using a sentiment analysis filter?

#### An Inadequate Solution: Limit the # of stories that can be requested. 
Obviously, the more URLs that we have added to our list of requests to make, the longer it will take to render results to the user. NewsApi defaults to retrieving 100 different stories, which would result in astronomically long wait times up to several minutes. We can remove the situation where a user is unsure whether or not progress is being made by ensuring that the number of requested stories is limited by capping the number of results that can be returned. 

#### A Better Solution: Multiprocessing 
Asyncronous code in Python seems to be a bit more complicated than in Javascript, and the number of options out there to implement parallel code is a bit overwhelming for someone like myself who is a relative beginner. However, I was able to come across a quick and clean way to reduce the total amount of time needed by using [Python's multiprocessing library](https://docs.python.org/3/library/multiprocessing.html)! We import the `Pool` object from the multiprocessing library and instantiate it with a numerical value that represents the number of worker processes. We can then call its .map() method which allows an iterable to be passed as the second arguement and for each of these elements to be passed into the function in the first argument. .map() blocks the main program and maintains the same order, although this doesn't matter to us as we will reorder the list anyway after we have obtained our sentiment analysis results. The callback function that we've given to .map() as its first argument contains all the logic that we need to parse an article with Newspaper given its url. 
This solution made a huge difference in increasing overall speed, although I have a hunch that I could implement an even more efficient solution if I understood Multiprocessing and Multithreading in Python more deeply. This is definitely an area that I intend to research further. Incidentally, this same logic is also used when making the six separate request to NewsApi when getting the top headlines for each category on the homepage. 
  
  
  
