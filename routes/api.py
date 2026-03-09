import re

from flask import Blueprint, request, jsonify, current_app

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _get_models():
    return current_app.extensions["models"]


@api_bp.route("/suggestions")
def suggestions():
    q = request.args.get("q", "").strip()
    mode = request.args.get("mode", "all").strip().lower()

    if not q or len(q) > 100:
        return jsonify([])

    q_lower = q.lower()
    models = _get_models()

    col_fields = {
        "flights": ["source", "destination"],
        "hotels":  ["destination"],
        "trains":  ["source", "destination"],
        "buses":   ["source", "destination"],
    }

    if mode in col_fields:
        targets = {mode: col_fields[mode]}
    else:
        targets = col_fields

    cities = set()
    for col_name, fields in targets.items():
        expr_names = {}
        proj_parts = []
        for idx, f in enumerate(fields):
            alias = f"#f{idx}"
            expr_names[alias] = f
            proj_parts.append(alias)
        items = models[col_name].table.scan(
            ProjectionExpression=", ".join(proj_parts),
            ExpressionAttributeNames=expr_names,
        ).get("Items", [])
        for item in items:
            for field in fields:
                val = item.get(field, "")
                if val and val.lower().startswith(q_lower):
                    cities.add(val)

    results = sorted(cities)[:10]
    return jsonify([{"name": c} for c in results])
