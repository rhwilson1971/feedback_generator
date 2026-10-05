# FG-35: Custom text during feedback generation

## Goal

Let the user edit a template's full text on the Generate page before substituting placeholder values. The edited text can be used once or saved as a new reusable template. The user approved editing the full text instead of a separate additional-text box.

## User flow

The Generate page contains an editable “Feedback text” textarea initialized with the saved template body. The user can insert, remove, or rewrite text anywhere, including adding or removing placeholders using the existing placeholder syntax.

Below the editor, show the values needed by the current body. Retain the source template's dropdown configuration and entered values for existing placeholders. Newly introduced placeholders use freeform inputs; removed placeholders no longer require values. Repeated placeholders share one input. Updating the editor preserves values for names that remain, and restoring a removed name during the same editing session restores its entered value.

Provide an explicit choice:

- **Use once** (default): generate from the edited body without saving a template.
- **Save as a new template**: reveal a required template name, suggested from the source name with a “Custom” suffix, and generate while saving the edited body.

The saved body retains placeholder tokens, rather than the personalized result. The new template inherits the source container, tags, ranking, and configurations for surviving placeholders. New placeholders are stored as freeform. It receives its own ID and timestamps and is appended using the existing template ordering convention. The original template remains intact. After saving, show a success message and generated feedback associated with the new template; subsequent generation and navigation use that template.

Preserve the edited body and submitted placeholder values on the result page so the user can revise and regenerate. Reset the save choice to Use once after a successful save to prevent accidental repeated copies. “Generate Another” opens a fresh generation form for the current template.

## Architecture and validation

Extend the existing generation form and POST handler, using a focused JavaScript helper for detecting placeholders and updating value controls. Use the existing server placeholder parser as the authority for which fields the submitted body needs. Derive existing placeholder configurations and inherited metadata from the database, not client-supplied hidden metadata.

Older submissions without an edited-body field continue generating from the stored body. Explicitly submitted blank or whitespace-only bodies are rejected. Require nonblank values for placeholders in the edited body and a nonblank name when saving. Unknown save modes are rejected. Validation errors return HTTP 400, show an accessible message, preserve the editor, selected mode, name, and entered values, and do not insert a new template.

Perform placeholder substitution in one pass so braces inside an entered value are treated as literal text rather than substituted again. Escape all text through the existing Jinja rendering. Continue recording freeform suggestions in the relevant container and preserve the existing copy button and browser-extension generated-feedback marker.

Validate before persistence. Insert a new template only for the explicit save mode, then render the generated result. No database schema migration is needed. Duplicate names follow the existing new-template naming policy; unique names are not a new requirement.

## Verification

Use isolated collection fixtures to verify one-off generation leaves templates unchanged; saving creates one template with the edited tokenized body and inherited metadata; removed and new placeholders work; replacement values containing placeholder-like text remain literal; validation failures preserve input and create nothing; legacy submissions still work; and result navigation uses the appropriate template.

Verify the JavaScript helper preserves values while changing placeholder controls and retains dropdown options. Run the existing Python and JavaScript suites. Inspect the browser flow for editing, dynamic fields, save-name visibility, generation, copy behavior, and returning to the container.

## Scope

This change does not add editing of tags, container, ranking, or dropdown definitions to the Generate page. Those remain available through the existing template form. Saving is a new-template operation, not an update to the source.

## Evidence

Tier 2 graph verification used the feedback_generator project, generation 2026-10-04T00:14:27Z. The generation handler currently substitutes values into the stored body, and template creation/copying already define persistence and metadata conventions. Coverage reported no recorded issue for app.py and templates/generate.html. templates/template_form.html has partial parsing at lines 27, 55, and 65; its full source was read directly, including these ranges. Graph coverage is a best-effort signal.
