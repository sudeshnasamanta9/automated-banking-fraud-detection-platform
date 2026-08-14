from flask import Blueprint, render_template, request, redirect, flash, session, url_for
import mysql.connector
import json
import os

# Define a Blueprint for rule configuration and management routes
rules_bp = Blueprint('rules', __name__)

def get_db_connection():
    """
    Establishes and returns a live connection to the MySQL database (kedge_db) 
    using environment variables for secure credential management.
    """
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="kedge_db"
    )

@rules_bp.route('/rules')
def rules_page():
    """
    Renders the dynamic rules configuration and visualization page.
    
    Validates user session authentication, queries the **rules_table** database table 
    to fetch all rule records, packs them into a structured JSON dictionary format, 
    and passes the payload to the template renderer.
    """
    # Step 1: Secure session authentication check; redirects to login if unauthenticated
    if 'user' not in session:
        return redirect('/')
    
    # Step 2: Establish database connection and query rule definitions from the rules_table
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rule_id, rule_name, rule_data FROM rules_table")
    rows = cursor.fetchall()
    conn.close()
    
    # Step 3: Parse and package rule records into a structured dictionary for frontend rendering
    rules_dict = {}
    for row in rows:
        rules_dict[row[0]] = {
            "name": row[1],
            "data": json.loads(row[2])
        }
        
    # Step 4: Render the template and pass serialized JSON rule payloads
    return render_template('rules.html', rules_json=json.dumps(rules_dict))

@rules_bp.route('/save-rule', methods=['POST'])
def save_rule_handler():
    """
    Handles the creation or updating of custom fraud detection rules.
    
    Validates user session, extracts dynamic form parameters and condition matrices, 
    packs configuration settings into a JSON payload, and persists or updates records 
    in the **rules_table** database table using an upsert query.
    """
    # Step 1: Secure session authentication check to block unauthorized access
    if 'user' not in session:
        return redirect('/')
        
    # Step 2: Extract base rule attributes from the submitted configuration form
    rule_id = request.form.get('rule_id')
    name = request.form.get('rule_name')
    desc = request.form.get('description')
    
    # Step 3: Dynamically loop through form parameters to assemble the condition matrix
    conditions = []
    i = 1
    while f"param_{i}" in request.form:
        conditions.append({
            "field": request.form.get(f"param_{i}"),
            "operator": request.form.get(f"op_{i}"),
            "value": request.form.get(f"val_{i}"),
            "logical": request.form.get(f"logical_{i}")
        })
        i += 1
    
    # Pack all rule attributes and condition criteria into a standardized JSON structure
    packed_json = {
        "rule_id": rule_id,
        "rule_name": name,
        "description": desc,
        "risk_score": request.form.get('score'),
        "conditions_matrix": conditions
    }
    
    # Step 4: Save or update the rule configuration inside the rules_table using an SQL upsert
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = '''
        INSERT INTO rules_table (rule_id, rule_name, rule_data) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE rule_name=%s, rule_data=%s
    '''
    cursor.execute(sql, (rule_id, name, json.dumps(packed_json), name, json.dumps(packed_json)))
    conn.commit()
    conn.close()
    
    # Step 5: Flash success message and redirect back to the rules management interface
    flash(f"Rule '{name}' saved successfully!")
    return redirect(url_for('rules.rules_page'))

@rules_bp.route('/delete-rule/<rule_id>')
def delete_rule_handler(rule_id):
    """
    Handles the deletion of a specific fraud detection rule by its identifier.
    
    Validates user session, executes a DELETE query against the **rules_table** database table, 
    and handles success or error notification messages.
    """
    # Step 1: Secure session authentication check to block unauthorized access
    if 'user' not in session:
        return redirect('/')
        
    try:
        # Step 2: Establish database connection and delete the target rule from the rules_table
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rules_table WHERE rule_id = %s", (rule_id,))
        conn.commit()
        conn.close()
        
        flash(f"Rule '{rule_id}' was successfully deleted!", "success")
    except Exception as e:
        # Catch and flash any database failure exceptions cleanly
        flash(f"Failed to delete rule '{rule_id}'.", "failure")
        
    # Step 3: Redirect back to the rules management page
    return redirect(url_for('rules.rules_page'))