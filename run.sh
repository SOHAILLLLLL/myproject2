#!/bin/bash
# Start the Gunicorn server
exec gunicorn myproject.wsgi:application --bind 0.0.0.0:8080