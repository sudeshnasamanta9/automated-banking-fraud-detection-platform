import mysql.connector
import os
import time
import pickle
import schedule
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Establishes and returns a connection to the MySQL database."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="kedge_db"
    )

def clear_previous_data():
    """Resets transaction states for a fresh batch run while preserving alert history for the dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE transaction_details SET is_processed = 'N'")
        conn.commit()
        print(">>> Fresh Start: Reset transaction states (Preserved historical alerts for dashboard).")
    except Exception as e:
        print(f"Error resetting data: {e}")
    finally:
        cursor.close()
        conn.close()

def is_rule_engine_enabled():
    """Checks the system settings table to see if the rule engine toggle is turned ON."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM system_settings WHERE setting_name = 'rule_engine'")
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result and result[0] == 'ON'

def get_remaining_count():
    """Returns the count of unprocessed transactions remaining in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transaction_details WHERE is_processed = 'N'")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count

def get_rules_from_db():
    """Fetches all active rules dynamically from the rules table."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT rule_id, rule_name, rule_data FROM rules_table")
    rules = cursor.fetchall()
    cursor.close()
    conn.close()
    return rules

def load_models_dynamically(rules):
    """Loads machine learning pickle files dynamically using each rule's specific ID."""
    models = {}
    for rule in rules:
        rule_id = rule['rule_id']
        path = fr"D:\6th Sem\InternShip_26\Data\{rule_id}.pickle"
        
        if os.path.exists(path):
            with open(path, 'rb') as f:
                models[rule_id] = pickle.load(f)
        else:
            print(f"Warning: Pickle file for '{rule_id}' not found at {path}")
    return models

def check_single_rule(txn, rule_id, model):
    """Evaluates transaction features against a specific rule model and returns a boolean prediction."""
    if not model: 
        return False

    today = datetime.now()
    days_diff = (today - txn['aod']).days if isinstance(txn['aod'], datetime) else 0
    narration_lower = str(txn.get('narration', '')).lower()
    channel_upper = str(txn.get('channel', '')).strip().upper()
    dr_cr_upper = str(txn.get('dr_cr', '')).strip().upper()

    # Rule 1: GST Refund validation
    if rule_id == 'rule_custom_458':
        if days_diff >= 90:
            return False
        narration_val = 1 if 'gst' in narration_lower else 0
        cr_val = 1 if dr_cr_upper == 'CR' else 0
        f = [[days_diff, narration_val, cr_val]]

    # Rule 2: High value credit in new account validation
    elif rule_id == 'rule_custom_412':
        if days_diff >= 90 or float(txn['cumulative_credit']) <= 500000:
            return False
        narration_val = 0 if 'premature' in narration_lower else 1
        f = [[days_diff, narration_val, float(txn['cumulative_credit'])]]

    # Rule 3: New account followed by high activity/ATM withdrawal validation
    elif rule_id == 'rule_custom_703':
        if days_diff >= 30 or float(txn['cumulative_credit']) <= 50000 or float(txn['cumulative_debit']) <= 40000:
            return False
        channel_val = 1 if channel_upper == 'ATM' else 0
        f = [[days_diff, float(txn['cumulative_credit']), float(txn['cumulative_debit']), channel_val]]
    else:
        f = [[days_diff, float(txn['cumulative_credit']), float(txn['cumulative_debit']), 1]]
        
    try:
        prediction = model.predict(f)[0]
        return prediction == 1
    except Exception as e:
        print(f"Prediction error for {rule_id}: {e}")
        return False

def process_batch():
    """Fetches a batch of transactions with running totals, runs them through the rule models, and logs alerts."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    rules = get_rules_from_db()
    models = load_models_dynamically(rules)

    cursor.execute("""
    SELECT *,
        SUM(CASE WHEN dr_cr = 'CR' THEN txn_amt ELSE 0 END) OVER (PARTITION BY acn ORDER BY txn_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as cumulative_credit,
        SUM(CASE WHEN dr_cr = 'DR' THEN txn_amt ELSE 0 END) OVER (PARTITION BY acn ORDER BY txn_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as cumulative_debit
    FROM transaction_details
    WHERE is_processed = 'N'
    ORDER BY txn_id ASC
    LIMIT 20
    """)
    transactions = cursor.fetchall()

    if not transactions:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] All transactions processed. Rule Engine completed.")
        
        # ---> UPDATE STATUS TO COMPLETED IN DATABASE <---
        cursor.execute("UPDATE system_settings SET status = 'COMPLETED' WHERE setting_name = 'rule_engine'")
        conn.commit()
        
        cursor.close()
        conn.close()
        return False

    processed_ids = []
    fraud_count = 0
    for txn in transactions:
        for rule in rules:
            rule_id = rule['rule_id']
            rule_name = rule['rule_name']
            model = models.get(rule_id)

            if check_single_rule(txn, rule_id, model):
                cursor.execute(
                    "INSERT INTO alert_details (acn, cid, rule_name, rule_id, alert_timestamp) VALUES (%s, %s, %s, %s, %s)",
                    (txn['acn'], txn['cid'], rule_name, rule_id, datetime.now())
                )
                fraud_count += 1
                print(f"ALERT: {rule_name} ({rule_id}) triggered for acn {txn['acn']}")

        processed_ids.append(txn['txn_id'])

    if processed_ids:
        format_strings = ','.join(['%s'] * len(processed_ids))
        cursor.execute(f"UPDATE transaction_details SET is_processed = 'Y' WHERE txn_id IN ({format_strings})", tuple(processed_ids))

    conn.commit()

    remaining = get_remaining_count()
    print(f"Batch processed: {len(transactions)} records. Fraud alerts: {fraud_count}. Total remaining: {remaining}")

    cursor.close()
    conn.close()
    return True

def run_scheduler_task():
    """Wrapper function executed by the scheduler to check settings and process batches."""
    if is_rule_engine_enabled():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Rule Engine ON: Processing batch...")
        has_more = process_batch()
        if not has_more:
            print("Stopping scheduler as all data is processed.")
            schedule.clear()
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Rule Engine OFF: Skipping.")

def run_rule_engine():
    """Initializes and runs the continuous background scheduler loop for the rule engine."""
    clear_previous_data()
    print("Engine started. Running every 10 seconds...")
    schedule.every(10).seconds.do(run_scheduler_task)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_rule_engine()