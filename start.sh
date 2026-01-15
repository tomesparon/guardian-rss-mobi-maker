#!/bin/sh
# Start the cron service in the background
cron
# Run the main application
exec python3 app.py
