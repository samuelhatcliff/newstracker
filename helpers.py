from models import db, User, Query
from sent_analysis import subjectize, polarize, parse_async
from flask import session, g

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
        query = Query(user_id=g.user.id,
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
