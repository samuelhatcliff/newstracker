from models import db, QueriedStory, User, QueriedStory, TestQ
from sent_analysis import subjectize, polarize
from flask import session, g


"""Helper Functions"""


def order_pol():
    """Loops over a User's Queried Stories results, orders by polarity,
    then filters out stories with no SA results"""
    user = User.query.get(g.user.id)
    if user.queried_stories:
        results = []
        for story in user.queried_stories:
            # WRITE PARALLEL AXIOS REQUESTS
            id = story.id
            score = polarize(story)

            if not score:
                QueriedStory.query.filter_by(story_id=id).delete()
                db.session.commit()

            else:
                result = score['article_res']['result']
                story.pol = str(result)
                db.session.commit()

        for result in user.queried_stories:
            results.append(result)

        ordered = sorted(user.queried_stories,
                         key=lambda story: story.pol,
                         reverse=True)

        return ordered


def order_sub():
    """Loops over a User's Queried Stories results, orders by subjectivity,
    then filters out stories with no SA results"""
    user = User.query.get(g.user.id)
    if user.queried_stories:
        for story in user.queried_stories:
            id = story.id
            score = subjectize(story)
            if score == None:
                QueriedStory.query.filter_by(story_id=id).delete()
                db.session.commit()
            else:
                story.sub = str(score['measure'])
                db.session.commit()
        ordered = sorted(user.queried_stories,
                         key=lambda story: story.sub, reverse=True)
        # CHANGE THESE SO THAT THEY SORT BY SUBJECTIVITY NUMBERS NOT RESULT SAME WITH POLARITY
        # ASK TA IF THEY KNOW OF PROGRESS BAR
        return ordered


def transfer_db_query_to_session(query):
    """Converts a saved query to session[dict]"""
    dict = {}
    dict['keyword'] = query.keyword
    dict['source'] = query.source
    dict['quantity'] = query.quantity
    dict['date_from'] = query.date_from
    dict['date_to'] = query.date_to
    dict['language'] = query.language
    dict['sa'] = query.sa
    dict['sort_by'] = query.sort_by
    return dict


def make_session_query(form):
    dict = {}
    dict['keyword'] = form.keyword.data
    dict['source'] = form.source.data
    dict['quantity'] = form.quantity.data
    dict['date_from'] = form.date_from.data
    dict['date_to'] = form.date_to.data
    dict['language'] = form.language.data

    if form.sort_by.data == "subjectivity" or form.sort_by.data == "polarity":
        dict['sa'] = form.sort_by.data
        dict['sort_by'] = 'relevancy'
    else:
        dict['sort_by'] = form.sort_by.data
        dict['sa'] = None
    session['dict'] = dict

    return dict


def add_saved_query(user_id, form):
    """Adds saved query to associated user in db"""
    user = User.query.get(user_id)
    keyword = form.keyword.data
    source = form.source.data
    quantity = form.quantity.data
    date_from = form.date_from.data
    date_to = form.date_to.data
    language = form.language.data
    default = form.default.data
    if form.sort_by.data == "subjectivity" or form.sort_by.data == "polarity":
        sa = form.sort_by.data
        sort_by = 'relevancy'
    else:
        sort_by = form.sort_by.data
        sa = None
        query = TestQ(user_id=g.user.id,
                      keyword=keyword,
                      source=source,
                      quantity=quantity,
                      date_from=date_from,
                      date_to=date_to,
                      language=language,
                      default=default,
                      type="detailed_search",
                      sa=sa,
                      sort_by=sort_by
                      )

        db.session.add(query)
        db.session.commit()
        user.saved_queries.append(query)
