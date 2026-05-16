import re
from datetime import datetime, timezone

from bson import ObjectId
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from database import get_templates_collection

app = Flask(__name__)
app.secret_key = "feedback-generator-secret-key"

PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_placeholders_from_body(body: str) -> list[str]:
    """Return unique placeholder names in order of first appearance."""
    seen = set()
    result = []
    for match in PLACEHOLDER_RE.finditer(body):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def _build_placeholders_from_form(form, body: str) -> list[dict]:
    """Build the placeholders sub-document list from the submitted form data."""
    names = _parse_placeholders_from_body(body)
    placeholders = []
    for i, name in enumerate(names):
        input_type = form.get(f"ph_type_{name}", "freeform")
        options = []
        if input_type == "dropdown":
            raw = form.get(f"ph_options_{name}", "")
            options = [o.strip() for o in raw.split("\n") if o.strip()]
        placeholders.append({
            "name": name,
            "input_type": input_type,
            "display_order": i,
            "options": options,
        })
    return placeholders


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    templates = list(get_templates_collection().find().sort("sort_order", 1))
    return render_template("index.html", templates=templates)


@app.route("/templates/new")
def new_template():
    return render_template("template_form.html", template=None)


@app.route("/templates", methods=["POST"])
def create_template():
    name = request.form.get("name", "").strip()
    body = request.form.get("body", "").strip()

    if not name or not body:
        flash("Name and body are required.", "danger")
        return redirect(url_for("new_template"))

    placeholders = _build_placeholders_from_form(request.form, body)
    now = datetime.now(timezone.utc)

    # New templates go to the end of the list
    last = get_templates_collection().find_one(sort=[("sort_order", -1)])
    next_order = (last["sort_order"] + 1) if last and "sort_order" in last else 0

    get_templates_collection().insert_one({
        "name": name,
        "body": body,
        "placeholders": placeholders,
        "sort_order": next_order,
        "created_at": now,
        "updated_at": now,
    })

    flash("Template created!", "success")
    return redirect(url_for("index"))


@app.route("/templates/<template_id>/edit")
def edit_template(template_id):
    tpl = get_templates_collection().find_one({"_id": ObjectId(template_id)})
    if not tpl:
        flash("Template not found.", "danger")
        return redirect(url_for("index"))
    return render_template("template_form.html", template=tpl)


@app.route("/templates/<template_id>/update", methods=["POST"])
def update_template(template_id):
    name = request.form.get("name", "").strip()
    body = request.form.get("body", "").strip()

    if not name or not body:
        flash("Name and body are required.", "danger")
        return redirect(url_for("edit_template", template_id=template_id))

    placeholders = _build_placeholders_from_form(request.form, body)

    get_templates_collection().update_one(
        {"_id": ObjectId(template_id)},
        {"$set": {
            "name": name,
            "body": body,
            "placeholders": placeholders,
            "updated_at": datetime.now(timezone.utc),
        }},
    )

    flash("Template updated!", "success")
    return redirect(url_for("index"))


@app.route("/templates/<template_id>/delete", methods=["POST"])
def delete_template(template_id):
    get_templates_collection().delete_one({"_id": ObjectId(template_id)})
    flash("Template deleted.", "success")
    return redirect(url_for("index"))


@app.route("/templates/<template_id>/generate")
def generate_form(template_id):
    tpl = get_templates_collection().find_one({"_id": ObjectId(template_id)})
    if not tpl:
        flash("Template not found.", "danger")
        return redirect(url_for("index"))
    return render_template("generate.html", template=tpl, result=None)


@app.route("/templates/<template_id>/generate", methods=["POST"])
def generate_feedback(template_id):
    tpl = get_templates_collection().find_one({"_id": ObjectId(template_id)})
    if not tpl:
        flash("Template not found.", "danger")
        return redirect(url_for("index"))

    result = tpl["body"]
    for ph in tpl["placeholders"]:
        value = request.form.get(f"ph_{ph['name']}", "")
        result = result.replace("{" + ph["name"] + "}", value)

    return render_template("generate.html", template=tpl, result=result)


@app.route("/templates/reorder", methods=["POST"])
def reorder_templates():
    order = request.get_json()
    if not order or not isinstance(order, list):
        return jsonify({"error": "Invalid data"}), 400

    col = get_templates_collection()
    for i, template_id in enumerate(order):
        col.update_one(
            {"_id": ObjectId(template_id)},
            {"$set": {"sort_order": i}},
        )

    return jsonify({"ok": True})


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
