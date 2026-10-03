# FG-4: Shared template ranking scales

Status: Approved by the user on October 1, 2026. Implement inline in this session.

## Scope

Deliver FG-4 through its linked tickets: FG-17 (storage), FG-18 (configuration UI), FG-19 (optional template assignment), and FG-20 (filtering). Each template has at most one scale and one rank. Existing templates remain unranked without a migration. Ranking describes a template; it does not change generated feedback text or the existing drag order.

## Approaches considered

1. Shared scales managed on a dedicated Rankings page (recommended): reusable across containers, with enough room to edit scale entries clearly.
2. Shared scales embedded in Settings: fewer navigation items, but mixes content configuration with application preferences.
3. Scales created inline while editing templates: convenient initially, but complicates editing shared scales and understanding effects on other templates.

## User workflow

- Add a Rankings navigation link and page listing scales and their usage counts.
- Create a scale with a unique name and one or more rows containing a positive integer rank number and a description. Numbers may have gaps and are displayed in ascending order; their meaning is defined by the user rather than assumed to mean better or worse.
- Allow adding/removing rows in the scale form, renaming scales, and editing rank descriptions.
- Template create/edit forms default to Unranked. Selecting a scale reveals its ranks; selecting a rank is required when a scale is selected. Changing scales clears the old rank selection. Choosing Unranked clears both values.
- Show a compact badge on ranked templates, for example Completion · 1 — Completed. Unranked templates have no badge.
- Copying a template or container preserves the scale and rank references. Copies reuse the shared scale.

## Filtering

- Add a scale dropdown beside the existing filters with All rankings, Unranked, and each named scale.
- Choosing a scale shows templates using that scale and enables an optional rank dropdown with All ranks and the scale's entries.
- Choosing a rank further restricts results to that rank within the chosen scale.
- Combine ranking, container, name, and tag filters with AND. The existing tag filter continues to match any selected tag.
- Changing scales resets the rank filter. The main Clear action resets all filters, including rankings, and restores the existing collapsed state.
- Matching containers expand; containers with no matching templates hide; no results uses the existing empty message.

## Storage and validation

Use a MongoDB ranking_scales collection with _id, name, name_key, ranks, created_at, and updated_at. name_key is the trimmed, casefolded name and has a unique index. Each rank is {id: positive integer, description: nonblank string}; rank IDs are unique within a scale.

Templates store ranking_scale_id and ranking_rank_id, both null for unranked templates. Missing fields also mean unranked. Rank IDs are stable numeric identifiers; changing a number is treated as removing that rank and adding another.

Validate all writes on the server: nonblank unique scale names, at least one rank, positive integer rank IDs, no duplicate IDs, nonblank descriptions, valid scale references, and membership of the selected rank in that scale. Reject malformed IDs and invalid submissions with a clear message and preserved form input; do not partially save invalid data.

Block deletion of a scale referenced by templates, explaining that those templates must be unranked or reassigned first. Similarly block removal or renumbering of any referenced rank. Renaming a scale or changing a rank description updates displayed labels everywhere through shared references. Unused scales and ranks can be removed with confirmation. This avoids silently changing template classifications.

## Implementation boundaries

- database.py: expose the scale collection using the existing connection helper.
- rankings.py: scale validation, lookup, unique-index initialization, and ranking-management routes in a Flask blueprint; registration occurs in app.py. Initialize the unique index lazily on ranking writes, with duplicate errors translated to user-facing validation.
- app.py: load scales for template and index pages; validate and save template ranking references; preserve references in both copy paths.
- templates/rankings.html and templates/ranking_form.html: scale management following the app's existing Bootstrap and theme styles.
- templates/base.html, template_form.html, and index.html: navigation, assignment fields, badges, and filter controls.
- static/rankings.js: dynamic scale rows and dependent rank selection. static/app.js extends existing filtering and Clear behavior.

## Verification

Write failing tests before implementation for scale CRUD/validation, duplicate names, referenced-scale/rank deletion guards, optional assignment, invalid rank/scale pairs, legacy unranked templates, and both copy paths. Stub all database collections used by rendered pages, including settings, so the suite does not wait on a live MongoDB instance.

JavaScript tests cover dependent selectors, rank row controls, combined filters, Unranked, empty results, scale changes, and full Clear behavior. Run the Python and JavaScript suites and verify in a browser: create/edit scales, assign/unrank templates, filter, copy, deletion guards, and light/dark presentation. If browser or database access is unavailable, report the exact verification gap.

## Completion

Prepare a reviewable implementation and PR covering FG-4 and FG-17 through FG-20. Report checks and any remaining limitations. Jira completion requires evidence that the feature is working; do not close tickets merely because a draft implementation exists.
