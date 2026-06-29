import os
import re
from datetime import datetime, timezone

from bson import ObjectId
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from database import get_containers_collection, get_templates_collection

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "feedback-generator-secret-key")

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
    containers = list(get_containers_collection().find().sort("sort_order", 1))
    templates = list(get_templates_collection().find().sort("sort_order", 1))
    grouped = {}
    uncategorized = []
    for tpl in templates:
        cid = tpl.get("container_id")
        if cid:
            grouped.setdefault(cid, []).append(tpl)
        else:
            uncategorized.append(tpl)
    return render_template(
        "index.html",
        containers=containers,
        grouped=grouped,
        uncategorized=uncategorized,
    )


@app.route("/templates/new")
def new_template():
    containers = list(get_containers_collection().find().sort("sort_order", 1))
    return render_template("template_form.html", template=None, containers=containers)


@app.route("/templates", methods=["POST"])
def create_template():
    name = request.form.get("name", "").strip()
    body = request.form.get("body", "").strip()

    if not name or not body:
        flash("Name and body are required.", "danger")
        return redirect(url_for("new_template"))

    placeholders = _build_placeholders_from_form(request.form, body)
    raw_cid = request.form.get("container_id", "").strip()
    container_id = ObjectId(raw_cid) if raw_cid else None
    now = datetime.now(timezone.utc)

    # New templates go to the end of the list
    last = get_templates_collection().find_one(sort=[("sort_order", -1)])
    next_order = (last["sort_order"] + 1) if last and "sort_order" in last else 0

    get_templates_collection().insert_one({
        "name": name,
        "body": body,
        "placeholders": placeholders,
        "container_id": container_id,
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
    containers = list(get_containers_collection().find().sort("sort_order", 1))
    return render_template("template_form.html", template=tpl, containers=containers)


@app.route("/templates/<template_id>/update", methods=["POST"])
def update_template(template_id):
    name = request.form.get("name", "").strip()
    body = request.form.get("body", "").strip()

    if not name or not body:
        flash("Name and body are required.", "danger")
        return redirect(url_for("edit_template", template_id=template_id))

    placeholders = _build_placeholders_from_form(request.form, body)
    raw_cid = request.form.get("container_id", "").strip()
    container_id = ObjectId(raw_cid) if raw_cid else None

    get_templates_collection().update_one(
        {"_id": ObjectId(template_id)},
        {"$set": {
            "name": name,
            "body": body,
            "placeholders": placeholders,
            "container_id": container_id,
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
# Container routes
# ---------------------------------------------------------------------------

@app.route("/categories")
def list_categories():
    col = get_containers_collection()
    categories = col.distinct("category")
    return jsonify(sorted(categories))


@app.route("/containers/new")
def new_container():
    categories = get_containers_collection().distinct("category")
    return render_template("container_form.html", container=None, categories=categories)


@app.route("/containers", methods=["POST"])
def create_container():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip() or "Default"

    if not name:
        flash("Container name is required.", "danger")
        return redirect(url_for("new_container"))

    now = datetime.now(timezone.utc)
    last = get_containers_collection().find_one(sort=[("sort_order", -1)])
    next_order = (last["sort_order"] + 1) if last and "sort_order" in last else 0

    get_containers_collection().insert_one({
        "name": name,
        "category": category,
        "sort_order": next_order,
        "created_at": now,
        "updated_at": now,
    })

    flash("Container created!", "success")
    return redirect(url_for("index"))


@app.route("/containers/<container_id>/edit")
def edit_container(container_id):
    ctr = get_containers_collection().find_one({"_id": ObjectId(container_id)})
    if not ctr:
        flash("Container not found.", "danger")
        return redirect(url_for("index"))
    categories = get_containers_collection().distinct("category")
    return render_template("container_form.html", container=ctr, categories=categories)


@app.route("/containers/<container_id>/update", methods=["POST"])
def update_container(container_id):
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip() or "Default"

    if not name:
        flash("Container name is required.", "danger")
        return redirect(url_for("edit_container", container_id=container_id))

    get_containers_collection().update_one(
        {"_id": ObjectId(container_id)},
        {"$set": {
            "name": name,
            "category": category,
            "updated_at": datetime.now(timezone.utc),
        }},
    )

    flash("Container updated!", "success")
    return redirect(url_for("index"))


@app.route("/containers/<container_id>/delete", methods=["POST"])
def delete_container(container_id):
    get_containers_collection().delete_one({"_id": ObjectId(container_id)})
    get_templates_collection().update_many(
        {"container_id": ObjectId(container_id)},
        {"$set": {"container_id": None}},
    )
    flash("Container deleted. Its templates are now uncategorized.", "success")
    return redirect(url_for("index"))


@app.route("/containers/reorder", methods=["POST"])
def reorder_containers():
    order = request.get_json()
    if not order or not isinstance(order, list):
        return jsonify({"error": "Invalid data"}), 400

    col = get_containers_collection()
    for i, cid in enumerate(order):
        col.update_one({"_id": ObjectId(cid)}, {"$set": {"sort_order": i}})

    return jsonify({"ok": True})


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
