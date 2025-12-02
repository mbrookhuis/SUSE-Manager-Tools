#!/usr/bin/env python3
#
# (c) 2025 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support
# For question/suggestions/bugs mail: michael.brookhuis@suse.com
#
# Version: 2025-11-25
#
# Created by: SUSE Michael Brookhuis
#
# status database for SUSE Manager tools
#
# Releases:
# 2025-11-25 M.Brookhuis - initial release.
#
import os
import sqlite3
import re
import json
import sys
from datetime import datetime

import yaml
from flask import Flask, request, jsonify, g

def load_yaml(stream):
    """
    Load YAML data.
    """
    loader = yaml.Loader(stream)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


if not os.path.isfile(os.path.dirname(__file__) + "/smtdb.yaml"):
    print("ERROR: smtdb.yaml doesn't exist. Please create file")
    sys.exit(1)
else:
    with open(os.path.dirname(__file__) + '/smtdb.yaml') as h_cfg:
        SMTDB = load_yaml(h_cfg)


# --- Configuration ---
DATABASE_NAME = SMTDB['database']['name']
ALLOWED_STATUSES = SMTDB['database']['allowed_statuses']
ALLOWED_SERVICES = SMTDB['database']['allowed_services']

app = Flask(__name__)
# Set to false to see readable JSON output in browser/curl
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


# --- Database Initialization and Connection Handlers ---

def get_db():
    """Connects to the specific database."""
    # Use Flask's application context to ensure only one connection per request
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE_NAME)
        # Allows accessing columns by name instead of index
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Creates the database table if it does not exist."""
    with app.app_context():
        db = get_db()
        # hostname is used as the primary key, enforcing the "one host per db" rule.
        db.execute('''
                   CREATE TABLE IF NOT EXISTS status_records (
                                                                 hostname TEXT PRIMARY KEY,
                                                                 timestamp TEXT NOT NULL,
                                                                 status TEXT NOT NULL,
                                                                 service TEXT NOT NULL,
                                                                 comment TEXT
                   )
                   ''')
        db.commit()

# Initialize the database on startup
init_db()


# --- Helper Functions ---

def convert_rows_to_dicts(rows):
    """Converts a list of sqlite3.Row objects into a list of dictionaries."""
    return [dict(row) for row in rows]

def format_output(records, output_format):
    """Formats records into JSON, Text, or Raw (CSV-like) based on the format requested."""
    if output_format == 'json':
        return jsonify(records), 200

    # Text format (human-readable)
    if output_format == 'text':
        if not records:
            return 'No records found.\n', 200

        header = f"{'HOSTNAME':<20} | {'TIMESTAMP':<25} | {'STATUS':<10} | {'SERVICE':<15} | COMMENT\n"
        separator = '-' * (20 + 25 + 10 + 15 + 10) + '\n'
        body = ""
        for r in records:
            body += f"{r['hostname']:<20} | {r['timestamp']:<25} | {r['status']:<10} | {r['service']:<15} | {r['comment'] or ''}\n"

        return header + separator + body, 200

    # Raw format (CSV-like, no escaping for simplicity)
    if output_format == 'raw':
        if not records:
            return 'hostname,timestamp,status,service,comment\n', 200

        header = 'hostname,timestamp,status,service,comment\n'
        body = ""
        for r in records:
            body += f"{r['hostname']},{r['timestamp']},{r['status']},{r['service']},{r['comment'] or ''}\n"

        return header + body, 200

    return jsonify({"error": "Invalid output format specified. Use 'json', 'text', or 'raw'."}), 400


# --- API Endpoints ---

@app.route('/record', methods=['POST'])
def submit_record():
    """Endpoint for clients to submit or update a status record."""
    data = request.get_json()

    if not data or not all(k in data for k in ['hostname', 'status', 'service']):
        return jsonify({"error": "Missing required fields: hostname, status, service."}), 400

    hostname = data['hostname'].strip().lower()
    status = data['status'].strip().lower()
    service = data['service'].strip().lower()
    comment = data.get('comment', '').strip()
    timestamp = datetime.now().isoformat()

    # Validate status and service
    if status not in ALLOWED_STATUSES:
        return jsonify({"error": f"Invalid status '{status}'. Must be one of: {', '.join(ALLOWED_STATUSES)}"}), 400
    if service not in ALLOWED_SERVICES:
        return jsonify({"error": f"Invalid service '{service}'. Must be one of: {', '.join(ALLOWED_SERVICES)}"}), 400

    db = get_db()
    try:
        # Use INSERT OR REPLACE to achieve the required upsert/update logic
        # If hostname exists, the old record is replaced entirely.
        db.execute("""
            INSERT OR REPLACE INTO status_records
            (hostname, timestamp, status, service, comment)
            VALUES (?, ?, ?, ?, ?)
        """, (hostname, timestamp, status, service, comment))
        db.commit()
        return jsonify({"message": f"Record for host '{hostname}' successfully updated/inserted."}), 201
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@app.route('/status', methods=['GET'])
def get_status():
    """
    Endpoint to query status records.
    Filters: hostname (or wildcard), status, service.
    Output formats: json, text, raw.
    """
    host_filter = request.args.get('hostname')
    status_filter = request.args.get('status')
    service_filter = request.args.get('service')
    output = request.args.get('output', 'json').lower()

    db = get_db()

    # 1. Build the WHERE clause dynamically
    where_clauses = []
    params = []

    # Filter by specific status (e.g., ?status=error)
    if status_filter:
        status_filter = status_filter.strip().lower()
        if status_filter not in ALLOWED_STATUSES:
            return jsonify({"error": f"Invalid status filter: {status_filter}. Must be one of: {', '.join(ALLOWED_STATUSES)}"}), 400
        where_clauses.append("status = ?")
        params.append(status_filter)

    # Filter by specific service (e.g., ?service=system_update)
    if service_filter:
        service_filter = service_filter.strip().lower()
        if service_filter not in ALLOWED_SERVICES:
            return jsonify({"error": f"Invalid service filter: {service_filter}. Must be one of: {', '.join(ALLOWED_SERVICES)}"}), 400
        where_clauses.append("service = ?")
        params.append(service_filter)

    # Filter by hostname, supporting SQL LIKE wildcards (e.g., ?hostname=web% or ?hostname=%db)
    if host_filter:
        # Convert user-friendly * wildcard to SQL % wildcard
        sql_like_host = host_filter.replace('*', '%')
        where_clauses.append("hostname LIKE ?")
        params.append(sql_like_host.strip().lower())

    # 2. Construct the final query
    sql = "SELECT hostname, timestamp, status, service, comment FROM status_records"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    # 3. Execute and fetch
    try:
        cur = db.execute(sql, params)
        records = convert_rows_to_dicts(cur.fetchall())
        return format_output(records, output)
    except sqlite3.Error as e:
        return jsonify({"error": f"Query execution error: {str(e)}"}), 500


@app.route('/records', methods=['DELETE'])
def delete_records():
    """
    Endpoint to remove status records.
    Filters: hostname (or wildcard), status, service.
    No filters deletes all records.
    """
    host_filter = request.args.get('hostname')
    status_filter = request.args.get('status')
    service_filter = request.args.get('service')

    db = get_db()

    # 1. Build the WHERE clause dynamically
    where_clauses = []
    params = []

    if status_filter:
        status_filter = status_filter.strip().lower()
        if status_filter not in ALLOWED_STATUSES:
            return jsonify({"error": f"Invalid status filter: {status_filter}. Must be one of: {', '.join(ALLOWED_STATUSES)}"}), 400
        where_clauses.append("status = ?")
        params.append(status_filter)

    if service_filter:
        service_filter = service_filter.strip().lower()
        if service_filter not in ALLOWED_SERVICES:
            return jsonify({"error": f"Invalid service filter: {service_filter}. Must be one of: {', '.join(ALLOWED_SERVICES)}"}), 400
        where_clauses.append("service = ?")
        params.append(service_filter)

    if host_filter:
        # Convert user-friendly * wildcard to SQL % wildcard
        sql_like_host = host_filter.replace('*', '%')
        where_clauses.append("hostname LIKE ?")
        params.append(sql_like_host.strip().lower())

    # 2. Construct the final query
    sql = "DELETE FROM status_records"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
        msg = "Matching records deleted."
    else:
        msg = "All records deleted."

    # 3. Execute and commit
    try:
        cur = db.execute(sql, params)
        deleted_count = cur.rowcount
        db.commit()
        return jsonify({"message": msg, "deleted_count": deleted_count}), 200
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({"error": f"Deletion execution error: {str(e)}"}), 500


# --- Run the Service ---

if __name__ == '__main__':
    # You can change the port and host if needed
    print(f"Starting service on {SMTDB['database']['hostname']}:{SMTDB['database']['port']}. Database file is '{DATABASE_NAME}'.")
    app.run(host=SMTDB['database']['hostname'], port=SMTDB['database']['port'], debug=True)
