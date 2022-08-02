# newstracker

## Technology/Tools: 
Python, Flask, SQLAlchemy, Redis, NewsAPI, NLTK, Newspaper, Axios, WTForms, CSS, Bootstrap,


## Summary: 
  NewsTracker is an application designed to enhance and optimize the way a user interacts with news stories. 
  This is achieved primarily using a search engine that connects to [NewsAPI](https://newsapi.org/) which allows the user to narrow-down the content of their results.  
  Additional search parameters such as "Polarity" and "Subjectivity" use Natural Language Processing through Python's NLTK library to parse through 
  the html data given by the URL returned by NewsAPI, which will order a user's search results by the degree to which an article is objective or positive, 
  as well as attach specific Sentimental Analysis data to each story.
  Other features available to users include the ability to save stories that they want to refer back to later, as well save a specific search query as their 
  default so that the main headline page will show results based off of the user's default search query. Future features will include the ability for a user
  to save and title multiple search queries and folders containing saved stories, as well as visual representations of data gleaned from the app's SA features. 


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
 
## Data-Flows: 
  When NewsTracker loads its homepage, it automatically makes several API get requests to NewsAPI using the "Top Headlines" endpoint. This API only accepts one
  optional parameter, which is the category of top headlines requested by us to the API. The "Headlines" link in the navbar will make an API call to the same endpoint with no
  additional parameters aside from setting "language" to "en" (unless switched to a user's default search query, see below).
  
  Get requests that require additional API parameters (simple search in the navbar, advanced searches, or default search queries replacing a user's headlines page) need to use
  NewsAPI's "Get Everything" endpoint, which allows more specific arguments to be passed in to achieve our desired results. On our end, we use SQLalchemy to save the data contained
  within the search query itself as an object represented by the search-query table. This helps us access information from the search query globally, which relieves us of the need to use
  session or to be constantly passing the data into various routes as an argument. Another positive effect of storing the query data this way, is that it allows us to link queries
  to specific users, which will be useful in the future when the ability for a user to save various search queries that they have set themselves is implemented. 
  
  In every circumstance where we need to make a get request to NewsAPI, we use the function `api_call`, which can be found in the `api_calls` module. As you can imagine,
  this is where all of our logic related to our interactions with NewsAPI is located. Our `api_call` function determines the type of API call being made on our end (ie simple search,
  advanced search, top headlines), calls one of the functions that we have written below designated to specific types of requests on our end, and proceeds to call the 
  `save_to_db` function. This function uses our QueriedStory table (not to be confused with the table representing the query data itself) to save the data returned by NewsAPI as stories
  assigned to a particular user. This allows the results of these types of search queries to be retrieved globally and to be manipulated by SA results after they've been saved to our database. 
  These stories will be deleted from user.queried_stories the next time the function as called, which avoids unwanted stories from being attached to our 
  search results and saves us space in our own database. No story is permanently saved to our own database unless added to `user.saved_stories` by the user saving the story.
  
  SA data functions can be found in the `sent_analysis` module. The result of passing a particular story in to one of these functions is then committed to each story in our database.
  
  
## Challenges: 
  The free version of news API is only limited to 100 requests per day, and does not allow developers to access the entirety of a story's content. As a work-around, I've used the "Newspaper"
  parsing library in python to extract the actual content of a story by making a request to the story's URL given to us by the NewsAPI. As a downside, each time sentimental analysis data
  is being parsed, a separate HTTP request is made. This is not so problematic when SA data is being requested by the user for one particular story, but does cause less than ideal waiting
  times for a user that has entered a search query requesting the results to be sorted by polarity or subjectivity. Because of this, I've temporarily limited the amount of results that are able to be
  requested in the advanced search feature to 10 until I've added a progress window to set the user's mind at ease, as well as more logic to the form itself that warns the user of the time it may
  take to initiate such a query.
  
  
  
