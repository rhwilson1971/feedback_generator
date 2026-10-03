import os
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from database import (
    get_containers_collection,
    get_settings_collection,
    get_templates_collection,
)

import rankings

app = Flask(__name__)
app.register_blueprint(rankings.bp)
app.secret_key = os.environ.get("SECRET_KEY", "feedback-generator-secret-key")

PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

SETTINGS_DOC_ID = "app"

THEME_CHOICES = ("light", "dark", "system")

# Every setting must have an entry here. get_settings() layers stored values
# over these, so adding a key never breaks an existing install.
DEFAULT_SETTINGS = {
    "disable_password_manager_autofill": False,
    "theme": "system",
    "reopen_container_after_feedback": True,
}

# Most-recently-used placeholder values, keyed by (container_id, placeholder
# name) so every template in a container shares suggestions. In memory only:
# cleared when the app restarts.
MRU_LIMIT = 10
_placeholder_mru: dict[tuple, list[str]] = {}


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


def _parse_tags(raw: str) -> list[str]:
    """Split comma-separated tags, trimming blanks and case-insensitive duplicates."""
    tags, seen = [], set()
    for tag in raw.split(","):
        tag = " ".join(tag.split())
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)
    return tags


def _sorted_tags(tags) -> list[str]:
    """Unique tags sorted case-insensitively."""
    return sorted({t for t in tags if t}, key=str.lower)


def _all_tags() -> list[str]:
    """Every tag used on any template."""
    return _sorted_tags(get_templates_collection().distinct("tags"))


def _unique_template_name(name: str, container_id) -> str:
    """Return name, or name with a " (copy)" / " (copy N)" suffix if the
    container already holds a template with that name."""
    col = get_templates_collection()
    candidate = name
    n = 1
    while col.find_one({"name": candidate, "container_id": container_id}):
        candidate = f"{name} (copy)" if n == 1 else f"{name} (copy {n})"
        n += 1
    return candidate


def remember_placeholder_value(container_id, name: str, value: str) -> None:
    """Move `value` to the front of the MRU list for this container/placeholder."""
    value = value.strip()
    if not value:
        return
    key = (container_id, name)
    values = [v for v in _placeholder_mru.get(key, []) if v != value]
    _placeholder_mru[key] = [value, *values][:MRU_LIMIT]


def placeholder_suggestions(tpl: dict) -> dict[str, list[str]]:
    """Return recent values for each of the template's placeholders."""
    cid = tpl.get("container_id")
    return {
        ph["name"]: list(_placeholder_mru.get((cid, ph["name"]), []))
        for ph in tpl["placeholders"]
    }


def get_settings() -> dict:
    """Return app settings with stored values layered over the defaults."""
    stored = get_settings_collection().find_one({"_id": SETTINGS_DOC_ID}) or {}
    settings = dict(DEFAULT_SETTINGS)
    for key in DEFAULT_SETTINGS:
        if key in stored:
            settings[key] = stored[key]
    if settings["theme"] not in THEME_CHOICES:
        settings["theme"] = DEFAULT_SETTINGS["theme"]
    return settings


def save_settings(updates: dict) -> None:
    """Upsert the known settings keys found in `updates`."""
    changes = {k: v for k, v in updates.items() if k in DEFAULT_SETTINGS}
    if not changes:
        return
    changes["updated_at"] = datetime.now(timezone.utc)
    get_settings_collection().update_one(
        {"_id": SETTINGS_DOC_ID},
        {"$set": changes},
        upsert=True,
    )


@app.context_processor
def inject_settings():
    """Make `settings` available to every template."""
    return {"settings": get_settings()}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Render templates grouped by container with tag and ranking filter data."""
    scales = rankings.list_scales()
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
        all_tags=_sorted_tags(t for tpl in templates for t in tpl.get("tags", [])),
        ranking_scales=scales, ranking_options=rankings.scale_options(scales),
        ranking_labels=rankings.ranking_labels(scales),
    )


def _render_template_form(template=None, submitted=None, error=None, selected=""):
    """Render assignment controls and preserve submitted values after validation errors.

    Submitted values override template values. Use selected as the fallback
    container ID; unknown containers display as Uncategorized.
    """
    containers = list(get_containers_collection().find().sort("sort_order", 1))
    scales = rankings.list_scales()
    values = template or {}
    if submitted is not None:
        values = {
            "name": submitted.get("name", ""), "body": submitted.get("body", ""),
            "tags": _parse_tags(submitted.get("tags", "")),
            "placeholders": _build_placeholders_from_form(submitted, submitted.get("body", "")),
            "container_id": submitted.get("container_id", ""),
            "ranking_scale_id": submitted.get("ranking_scale_id", ""),
            "ranking_rank_id": submitted.get("ranking_rank_id", ""),
        }
    selected = str(values.get("container_id") or selected)
    if not any(str(c["_id"]) == selected for c in containers):
        selected = ""
    return render_template(
        "template_form.html", template=template, form_values=values, error=error,
        containers=containers, selected_container_id=selected, all_tags=_all_tags(),
        ranking_scales=scales, ranking_options=rankings.scale_options(scales),
        selected_scale_id=str(values.get("ranking_scale_id") or ""),
        selected_rank_id=str(values.get("ranking_rank_id") or ""),
    )


@app.route("/templates/new")
def new_template():
    """Render the new template form with a valid query container preselected.

    Missing or unknown container IDs default to Uncategorized.
    """
    return _render_template_form(selected=request.args.get("container_id", ""))


@app.route("/templates", methods=["POST"])
def create_template():
    """Save a new template and redirect to the index.

    Missing name/body, invalid rankings, or malformed container IDs redisplay
    submitted values with HTTP 400 without inserting a template.
    """
    name = request.form.get("name", "").strip()
    body = request.form.get("body", "").strip()

    try:
        if not name or not body:
            raise ValueError("Name and body are required.")
        ranking = rankings.template_ranking(request.form)
        raw_cid = request.form.get("container_id", "").strip()
        container_id = ObjectId(raw_cid) if raw_cid else None
    except (ValueError, InvalidId) as error:
        return _render_template_form(submitted=request.form, error=str(error)), 400

    placeholders = _build_placeholders_from_form(request.form, body)
    now = datetime.now(timezone.utc)

    # New templates go to the end of the list
    last = get_templates_collection().find_one(sort=[("sort_order", -1)])
    next_order = (last["sort_order"] + 1) if last and "sort_order" in last else 0

    get_templates_collection().insert_one({
        "name": name,
        "body": body,
        "placeholders": placeholders,
        "tags": _parse_tags(request.form.get("tags", "")),
        **ranking,
        "container_id": container_id,
        "sort_order": next_order,
        "created_at": now,
        "updated_at": now,
    })

    flash("Template created!", "success")
    return redirect(url_for("index"))


@app.route("/templates/<template_id>/edit")
def edit_template(template_id):
    """Render an existing template for editing, redirecting if it is missing.

    A malformed template_id raises InvalidId rather than redirecting.
    """
    tpl = get_templates_collection().find_one({"_id": ObjectId(template_id)})
    if not tpl:
        flash("Template not found.", "danger")
        return redirect(url_for("index"))
    return _render_template_form(template=tpl)


@app.route("/templates/<template_id>/update", methods=["POST"])
def update_template(template_id):
    """Validate and save template edits, then redirect to the index.

    Return HTTP 404 for a malformed or unknown template ID. Missing name/body,
    invalid rankings, or malformed container IDs redisplay submitted values
    with HTTP 400 without updating the template.
    """
    name = request.form.get("name", "").strip()
    body = request.form.get("body", "").strip()

    try:
        source_id = ObjectId(template_id)
    except InvalidId:
        return "Template not found", 404
    tpl = get_templates_collection().find_one({"_id": source_id})
    if not tpl:
        return "Template not found", 404
    try:
        if not name or not body:
            raise ValueError("Name and body are required.")
        ranking = rankings.template_ranking(request.form)
        raw_cid = request.form.get("container_id", "").strip()
        container_id = ObjectId(raw_cid) if raw_cid else None
    except (ValueError, InvalidId) as error:
        return _render_template_form(template=tpl, submitted=request.form, error=str(error)), 400

    placeholders = _build_placeholders_from_form(request.form, body)

    get_templates_collection().update_one(
        {"_id": ObjectId(template_id)},
        {"$set": {
            "name": name,
            "body": body,
            "placeholders": placeholders,
            "tags": _parse_tags(request.form.get("tags", "")),
            **ranking,
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


@app.route("/templates/<template_id>/copy", methods=["POST"])
def copy_template(template_id):
    """Copy a template into the requested container, retaining tags and ranking references."""
    try:
        source_id = ObjectId(template_id)
        raw_cid = request.form.get("container_id", "").strip()
        container_id = ObjectId(raw_cid) if raw_cid else None
    except InvalidId:
        flash("Template or container not found.", "danger")
        return redirect(url_for("index"))

    source = get_templates_collection().find_one({"_id": source_id})
    if not source:
        flash("Template not found.", "danger")
        return redirect(url_for("index"))

    target_name = "Uncategorized"
    if container_id:
        target = get_containers_collection().find_one({"_id": container_id})
        if not target:
            flash("Container not found.", "danger")
            return redirect(url_for("index"))
        target_name = target["name"]

    now = datetime.now(timezone.utc)
    last = get_templates_collection().find_one(sort=[("sort_order", -1)])
    next_order = (last["sort_order"] + 1) if last and "sort_order" in last else 0

    get_templates_collection().insert_one({
        "name": _unique_template_name(source["name"], container_id),
        "body": source["body"],
        "placeholders": [dict(ph) for ph in source["placeholders"]],
        "tags": list(source.get("tags", [])),
        "ranking_scale_id": source.get("ranking_scale_id"),
        "ranking_rank_id": source.get("ranking_rank_id"),
        "container_id": container_id,
        "sort_order": next_order,
        "created_at": now,
        "updated_at": now,
    })

    flash(f"Copied '{source['name']}' to '{target_name}'.", "success")
    return redirect(url_for("index"))


@app.route("/templates/<template_id>/generate")
def generate_form(template_id):
    tpl = get_templates_collection().find_one({"_id": ObjectId(template_id)})
    if not tpl:
        flash("Template not found.", "danger")
        return redirect(url_for("index"))
    return render_template(
        "generate.html", template=tpl, result=None,
        suggestions=placeholder_suggestions(tpl),
    )


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
        if ph.get("input_type") != "dropdown":
            remember_placeholder_value(tpl.get("container_id"), ph["name"], value)

    return render_template(
        "generate.html", template=tpl, result=result,
        suggestions=placeholder_suggestions(tpl),
    )


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


@app.route("/containers/<container_id>/copy", methods=["POST"])
def copy_container(container_id):
    """Duplicate a container and its templates, retaining their shared ranking references."""
    try:
        source_id = ObjectId(container_id)
    except InvalidId:
        flash("Container not found.", "danger")
        return redirect(url_for("index"))

    source = get_containers_collection().find_one({"_id": source_id})
    if not source:
        flash("Container not found.", "danger")
        return redirect(url_for("index"))

    name = request.form.get("name", "").strip() or f"{source['name']} (copy)"
    now = datetime.now(timezone.utc)

    last = get_containers_collection().find_one(sort=[("sort_order", -1)])
    next_order = (last["sort_order"] + 1) if last and "sort_order" in last else 0
    new_id = get_containers_collection().insert_one({
        "name": name,
        "category": source.get("category", "Default"),
        "sort_order": next_order,
        "created_at": now,
        "updated_at": now,
    }).inserted_id

    templates = list(
        get_templates_collection().find({"container_id": source_id}).sort("sort_order", 1)
    )
    last_tpl = get_templates_collection().find_one(sort=[("sort_order", -1)])
    tpl_order = (last_tpl["sort_order"] + 1) if last_tpl and "sort_order" in last_tpl else 0
    for i, tpl in enumerate(templates):
        get_templates_collection().insert_one({
            "name": tpl["name"],
            "body": tpl["body"],
            "placeholders": [dict(ph) for ph in tpl["placeholders"]],
            "tags": list(tpl.get("tags", [])),
            "ranking_scale_id": tpl.get("ranking_scale_id"),
            "ranking_rank_id": tpl.get("ranking_rank_id"),
            "container_id": new_id,
            "sort_order": tpl_order + i,
            "created_at": now,
            "updated_at": now,
        })

    count = len(templates)
    flash(
        f"Copied '{source['name']}' to '{name}' with {count} template{'s' if count != 1 else ''}.",
        "success",
    )
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
# Settings routes
# ---------------------------------------------------------------------------

@app.route("/settings")
def settings_page():
    return render_template("settings.html")


@app.route("/settings", methods=["POST"])
def update_settings():
    # An unchecked checkbox is absent from the form body, so absence == False.
    updates = {
        "disable_password_manager_autofill":
            "disable_password_manager_autofill" in request.form,
        "reopen_container_after_feedback":
            "reopen_container_after_feedback" in request.form,
    }
    theme = request.form.get("theme", "")
    if theme in THEME_CHOICES:
        updates["theme"] = theme
    save_settings(updates)
    flash("Settings saved.", "success")
    return redirect(url_for("settings_page"))


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5010)))
