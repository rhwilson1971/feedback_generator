"""Shared ranking scales: validation, template references, and management UI."""
import re
from datetime import datetime, timezone
from itertools import zip_longest

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from pymongo.errors import DuplicateKeyError

import database

bp = Blueprint('rankings', __name__)


def list_scales():
    """Return scales in case-insensitive name order without mutating storage."""
    return sorted(database.get_ranking_scales_collection().find(), key=lambda s: s['name_key'])


def scale_options(scales):
    """JSON-safe scale data for dependent rank selectors."""
    return [{'id': str(s['_id']), 'name': s['name'], 'ranks': s['ranks']} for s in scales]


def get_scale(scale_id):
    """Return the scale for a route ID; abort with HTTP 404 if invalid or missing."""
    try:
        oid = ObjectId(scale_id)
    except (InvalidId, TypeError):
        abort(404)
    scale = database.get_ranking_scales_collection().find_one({'_id': oid})
    if not scale:
        abort(404)
    return scale


def form_values(form):
    """Return the submitted name and rank rows without validation or trimming.

    Pair repeated rank_id and rank_description fields in order, filling missing
    partners with empty strings so malformed rows remain available for correction.
    """
    rows = [{'id': n, 'description': d} for n, d in zip_longest(
        form.getlist('rank_id'), form.getlist('rank_description'), fillvalue='')]
    return {'name': form.get('name', ''), 'ranks': rows}


def validate_scale(values):
    """Return trimmed labels, a casefolded name_key, and ranks in numeric order.

    Accept the name/ranks mapping from form_values. Raise ValueError for a
    blank name or description, no ranks, duplicate rank numbers, or invalid
    numbers. Rank IDs must contain 1-10 ASCII digits after trimming and have
    values from 1 through 2147483647; gaps are allowed.
    """
    name = values['name'].strip()
    if not name:
        raise ValueError('A scale name is required.')
    if not values['ranks']:
        raise ValueError('Add at least one rank.')
    ranks, seen = [], set()
    for row in values['ranks']:
        raw = str(row['id']).strip()
        if not re.fullmatch(r'[0-9]+', raw) or len(raw) > 10:
            raise ValueError('Rank numbers must be positive integers up to 2147483647.')
        number = int(raw)
        if not 1 <= number <= 2147483647:
            raise ValueError('Rank numbers must be positive integers up to 2147483647.')
        if number in seen:
            raise ValueError('Each rank number must be unique within its scale.')
        description = row['description'].strip()
        if not description:
            raise ValueError('Each rank needs a description.')
        seen.add(number)
        ranks.append({'id': number, 'description': description})
    return {'name': name, 'name_key': name.casefold(), 'ranks': sorted(ranks, key=lambda r: r['id'])}


def template_ranking(form):
    """Return ranking_scale_id and ranking_rank_id references for a template.

    A missing or blank scale clears both references to None, ignoring any rank.
    Otherwise, raise ValueError for an invalid or unknown scale or a rank that
    is not 1-10 ASCII digits naming a rank in that scale, after trimming.
    Database lookup errors propagate.
    """
    raw_scale = form.get('ranking_scale_id', '').strip()
    if not raw_scale:
        return {'ranking_scale_id': None, 'ranking_rank_id': None}
    try:
        sid = ObjectId(raw_scale)
    except (InvalidId, TypeError):
        raise ValueError('Choose a valid ranking scale.') from None
    scale = database.get_ranking_scales_collection().find_one({'_id': sid})
    if not scale:
        raise ValueError('That ranking scale no longer exists. Choose another or Unranked.')
    raw_rank = form.get('ranking_rank_id', '').strip()
    if not re.fullmatch(r'[0-9]+', raw_rank) or len(raw_rank) > 10:
        raise ValueError('Choose a rank from the selected scale.')
    rank = int(raw_rank)
    if not any(r['id'] == rank for r in scale['ranks']):
        raise ValueError('Choose a rank from the selected scale.')
    return {'ranking_scale_id': sid, 'ranking_rank_id': rank}


def ranking_labels(scales):
    """Resolve labels by shared references so edits appear on all templates."""
    return {str(s['_id']): {r['id']: f"{s['name']} · {r['id']} — {r['description']}"
                           for r in s['ranks']} for s in scales}


def save_scale(values, source=None):
    """Validate and insert a scale, or update the stored scale given by source.

    Accept values from form_values and an existing scale document as source.
    Raise ValueError for invalid values, a name already used (ignoring case and
    surrounding whitespace), or removal of a referenced rank number.
    Set timestamps and ensure a unique name_key index. DuplicateKeyError from
    insert/update becomes ValueError; index creation and other database errors
    propagate.
    """
    changes = validate_scale(values)
    col = database.get_ranking_scales_collection()
    duplicate = col.find_one({'name_key': changes['name_key']})
    if duplicate and (source is None or duplicate['_id'] != source['_id']):
        raise ValueError('A scale with that name already exists.')
    if source:
        kept = {r['id'] for r in changes['ranks']}
        for rank in source['ranks']:
            if rank['id'] not in kept and database.get_templates_collection().find_one(
                {'ranking_scale_id': source['_id'], 'ranking_rank_id': rank['id']}
            ):
                raise ValueError(f"Rank {rank['id']} is in use. Unrank or reassign its templates first.")
    changes['updated_at'] = datetime.now(timezone.utc)
    # Initialize lazily on writes; a unique index also catches concurrent name collisions.
    col.create_index('name_key', unique=True)
    try:
        if source:
            col.update_one({'_id': source['_id']}, {'$set': changes})
        else:
            changes['created_at'] = changes['updated_at']
            col.insert_one(changes)
    except DuplicateKeyError:
        raise ValueError('A scale with that name already exists.') from None


@bp.get('/rankings')
def index():
    """Render shared scales with the number of templates using each scale."""
    scales = list_scales()
    usages = {str(s['_id']): database.get_templates_collection().count_documents(
        {'ranking_scale_id': s['_id']}) for s in scales}
    return render_template('rankings.html', scales=scales, usages=usages)


@bp.get('/rankings/new')
def new():
    """Render a blank scale form with one initial rank row."""
    return render_template('ranking_form.html', scale=None,
                           values={'name': '', 'ranks': [{'id': 1, 'description': ''}]})


@bp.post('/rankings')
def create():
    """Create a scale, or return the submitted form with validation errors and HTTP 400."""
    values = form_values(request.form)
    try:
        save_scale(values)
    except ValueError as error:
        return render_template('ranking_form.html', scale=None, values=values, error=str(error)), 400
    flash('Ranking scale created!', 'success')
    return redirect(url_for('rankings.index'))


@bp.get('/rankings/<scale_id>/edit')
def edit(scale_id):
    """Render an existing scale for editing, or abort with HTTP 404."""
    scale = get_scale(scale_id)
    return render_template('ranking_form.html', scale=scale, values=scale)


@bp.post('/rankings/<scale_id>/update')
def update(scale_id):
    """Save scale edits and redirect to the scale list.

    Abort with HTTP 404 for an invalid or missing scale. Redisplay submitted
    values with HTTP 400 when save_scale raises ValueError.
    """
    scale = get_scale(scale_id)
    values = form_values(request.form)
    try:
        save_scale(values, source=scale)
    except ValueError as error:
        return render_template('ranking_form.html', scale=scale, values=values, error=str(error)), 400
    flash('Ranking scale updated!', 'success')
    return redirect(url_for('rankings.index'))


@bp.post('/rankings/<scale_id>/delete')
def delete(scale_id):
    """Delete an unused scale, or flash a warning when templates still reference it.

    Redirect to the scale list in either case; abort with HTTP 404 for an
    invalid or missing scale.
    """
    scale = get_scale(scale_id)
    if database.get_templates_collection().find_one({'ranking_scale_id': scale['_id']}):
        flash('This scale is in use. Unrank or reassign its templates before deleting it.', 'danger')
    else:
        database.get_ranking_scales_collection().delete_one({'_id': scale['_id']})
        flash('Ranking scale deleted.', 'success')
    return redirect(url_for('rankings.index'))
