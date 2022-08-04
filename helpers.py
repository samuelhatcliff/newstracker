from models import db, User, Query
from sent_analysis import subjectize, polarize, parse_async
from flask import session

"""Helper Functions"""

def order_pol():
    """Loops over session results, filters out stories with no SA results, 
    then orders by polarity"""
    results = parse_async(session['results'])
    for story in results:
        score = polarize(story, parsed=True)
        if not score:
            story['pol'] = None
        else:
            story['pol'] = score['article_res']['result']
    session['results'] = [story for story in results if story['pol']]
    results = session['results']
    not_negative = [
        story for story in results if story['pol'][0] is not "-"]
    negative = [
        story for story in results if story['pol'][0] is "-"]
    ordered_neg = sorted(negative,
                            key=lambda story: story['pol'])
    ordered_not_neg = sorted(not_negative,
                                key=lambda story: story['pol'], reverse=True)
    ordered = ordered_not_neg + ordered_neg
    return ordered


def order_sub():
    """Loops over session results, filters out stories with no SA results, 
    then orders by subjectivity"""
    results = parse_async(session['results'])
    for story in results:
        score = subjectize(story, parsed=True)
        if not score:
            story['sub'] = None
        else:
            story['sub'] = str(score['measure'])
    session['results'] = [story for story in results if story['sub']]
    results = session['results']
    ordered = sorted(results,
                        key=lambda story: story['sub'], reverse=True)
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
    if "query" in session:
        session.pop("query")

    session["query"] = dict
    return dict


def make_session_query(form):
    query = {}
    query['keyword'] = form.keyword.data
    query['source'] = form.source.data
    query['quantity'] = form.quantity.data
    query['date_from'] = form.date_from.data
    query['date_to'] = form.date_to.data
    query['language'] = form.language.data
    if form.sort_by.data == "subjectivity" or form.sort_by.data == "polarity":
        query['sa'] = form.sort_by.data
        query['sort_by'] = 'relevancy'
    else:
        query['sort_by'] = form.sort_by.data
        query['sa'] = None
    session['query'] = query
    return query


def add_saved_query(user_id, form):
    """Adds saved query to associated user in db"""
    keyword = form.keyword.data
    source = form.source.data
    quantity = form.quantity.data
    date_from = form.date_from.data
    date_to = form.date_to.data
    language = form.language.data
    default = form.default.data
    name = form.name.data
    if form.sort_by.data == "subjectivity" or form.sort_by.data == "polarity":
        sa = form.sort_by.data
        sort_by = 'relevancy'
    else:
        sort_by = form.sort_by.data
        sa = None
    #TODO: query sqlalchemy object needs name. build responsive form that asks if query should be default and allows space to name query
    query = Query(
                      name = name,
                      user_id = user_id,
                      keyword=keyword,
                      source=source,
                      quantity=quantity,
                      language=language,
                      default=default,
                      type="detailed_search",
                      sa=sa,
                      sort_by=sort_by,
                      date_from=date_from,
                      date_to=date_to,
                      )

    db.session.add(query)
    db.session.commit()
