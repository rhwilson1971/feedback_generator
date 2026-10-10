# Database outage page

Approved design: database connection failures display “We'll be right back” with a brief explanation and a Try again link to the home page. Return HTTP 503, Retry-After: 30, and Cache-Control: no-store. Log exception details on the server only.

Register one application-wide ConnectionFailure handler, covering reconnection and server-selection failures, including blueprint routes. Render a self-contained Jinja template directly without Flask context processors, because normal template rendering reads database settings. Do not catch unrelated programming or validation errors.

Background fetch responses carry X-Database-Unavailable: 1. A browser fetch wrapper navigates to /unavailable only for marked 503 responses. This route renders without database access. Manual retry uses GET to the home page and does not replay failed writes. No automatic retry or database timeout changes.

Verify settings-render failures, write failures, no recursive settings calls, private exception details, recovery, and unrelated error handling. Test background navigation and normal responses. Run the full Python and JavaScript suites.
