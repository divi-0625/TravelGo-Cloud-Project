from flask import (
    Blueprint, render_template, request, current_app, session,
)

search_bp = Blueprint("search", __name__)


def _get_models():
    return current_app.extensions["models"]


@search_bp.route("/search")
def search_page():
    models = _get_models()
    tab = request.args.get("tab", "flights")
    listings = {
        "flights": models["flights"].get_all()[:12],
        "hotels":  models["hotels"].get_all()[:12],
        "trains":  models["trains"].get_all()[:12],
        "buses":   models["buses"].get_all()[:12],
    }
    return render_template("search.html", active_tab=tab, listings=listings)


@search_bp.route("/results")
def results():
    models = _get_models()
    tab = request.args.get("type", "flights")
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    date = request.args.get("date", "").strip()
    sort_by = request.args.get("sort", "price")
    max_price = request.args.get("max_price", "")
    min_rating = request.args.get("min_rating", "")

    items = []
    date_relaxed = False

    if tab == "flights":
        items = models["flights"].search(source, destination, date or None)
    elif tab == "hotels":
        items = models["hotels"].search(destination, date or None)
    elif tab == "trains":
        items = models["trains"].search(source, destination, date or None)
    elif tab == "buses":
        items = models["buses"].search(source, destination, date or None)

    if not items and date:
        date_relaxed = True
        if tab == "flights":
            items = models["flights"].search(source, destination, None)
        elif tab == "hotels":
            items = models["hotels"].search(destination, None)
        elif tab == "trains":
            items = models["trains"].search(source, destination, None)
        elif tab == "buses":
            items = models["buses"].search(source, destination, None)
    elif items and date:
        date_field = "checkin" if tab == "hotels" else "date"
        exact_hits = [i for i in items if i.get(date_field) == date]
        if exact_hits:
            items.sort(key=lambda x: (0 if x.get(date_field) == date else 1))
            date_relaxed = False
        else:
            date_relaxed = "nearby"

    if max_price:
        try:
            mp = float(max_price)
            items = [i for i in items if i.get("price", 0) <= mp]
        except ValueError:
            pass

    if min_rating and tab == "hotels":
        try:
            mr = float(min_rating)
            items = [i for i in items if i.get("rating", 0) >= mr]
        except ValueError:
            pass

    if sort_by == "price":
        items.sort(key=lambda x: x.get("price", 0))
    elif sort_by == "duration":
        items.sort(key=lambda x: x.get("duration", ""))
    elif sort_by == "rating" and tab == "hotels":
        items.sort(key=lambda x: x.get("rating", 0), reverse=True)

    price_alerts = [i for i in items if i.get("price", 99999) < 1000]

    return render_template(
        "results.html",
        items=items,
        search_type=tab,
        source=source,
        destination=destination,
        date=date,
        sort_by=sort_by,
        price_alerts=price_alerts,
        date_relaxed=date_relaxed,
    )
