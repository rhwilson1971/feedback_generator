"""Database-independent outage responses shared by all Flask routes."""

from flask import Response, url_for
from pymongo.errors import ConnectionFailure


def register_availability(app):
    """Register an outage route and connection-error handler on the Flask app."""
    def unavailable():
        """Return a non-cacheable 503 page without running context processors."""
        html = app.jinja_env.get_template('unavailable.html').render(
            retry_url=url_for('index')
        )
        return Response(html, status=503, headers={
            'Retry-After': '30',
            'Cache-Control': 'no-store',
            'X-Database-Unavailable': '1',
        }, mimetype='text/html')

    def handle_connection_failure(error):
        """Log the database exception and return the friendly outage response."""
        app.logger.error('Database connection unavailable', exc_info=error)
        return unavailable()

    app.add_url_rule('/unavailable', 'unavailable', unavailable)
    app.register_error_handler(ConnectionFailure, handle_connection_failure)
