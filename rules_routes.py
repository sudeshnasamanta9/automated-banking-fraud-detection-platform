from flask import Blueprint, render_template, request, redirect, flash, session, url_for
import mysql.connector
import json
import os

rules_bp = Blueprint('rules', __name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="kedge_db"
    )

@rules_bp.route('/rules')
def rules_page():
    if 'user' not in session:
        return redirect('/')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    # Corrected column names to match your DB schema (rule_data)
    cursor.execute("SELECT rule_id, rule_name, rule_data FROM rules_table")
    rows = cursor.fetchall()
    conn.close()
    
    rules_dict = {}
    for row in rows:
        rules_dict[row[0]] = {
            "name": row[1],
            "data": json.loads(row[2])
        }
        
    return render_template('rules.html', rules_json=json.dumps(rules_dict))

@rules_bp.route('/save-rule', methods=['POST'])
def save_rule_handler():
    if 'user' not in session:
        return redirect('/')
        
    rule_id = request.form.get('rule_id')
    name = request.form.get('rule_name')
    desc = request.form.get('description')
    
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
    
    packed_json = {
        "rule_id": rule_id,
        "rule_name": name,
        "description": desc,
        "risk_score": request.form.get('score'),
        "conditions_matrix": conditions
    }
    
    # Save to MySQL using correct column name 'rule_data'
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
    
    flash(f"Rule '{name}' saved successfully!")
    return redirect(url_for('rules.rules_page'))

@rules_bp.route('/delete-rule/<rule_id>')
def delete_rule_handler(rule_id):
    if 'user' not in session:
        return redirect('/')
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rules_table WHERE rule_id = %s", (rule_id,))
        conn.commit()
        conn.close()
        flash(f"Rule '{rule_id}' was successfully deleted!", "success")
    except Exception as e:
        flash(f"Failed to delete rule '{rule_id}'.", "failure")
        
    return redirect(url_for('rules.rules_page'))