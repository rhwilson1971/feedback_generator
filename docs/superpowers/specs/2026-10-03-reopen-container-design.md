# FG-31: Reopen the template's container

Approved by the user on October 3, 2026.

Back to templates on the generation page carries the template ID in a return_template query parameter when the new reopen_container_after_feedback setting is enabled (default true). The index finds that template in its current rendered container, expands the container, updates accordion accessibility state, and scrolls the container into view. Uncategorized is supported. Missing/deleted templates and malformed identifiers leave the normal list unchanged. No browser storage or session memory is needed.

Restoration runs once after filter initialization; later filtering and Clear retain existing behavior. Settings uses the existing MongoDB settings document and checkbox conventions. Disabling the preference also prevents restoration from old bookmarked return URLs.

Regression tests cover return links before/after generation, defaults and saving, disabling restoration, current-container lookup, Uncategorized, missing targets, scrolling, and subsequent filtering.
