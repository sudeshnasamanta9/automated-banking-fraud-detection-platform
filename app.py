from dotenv import load_dotenv
load_dotenv()
import os
import re
import mysql.connector
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.io as pio
import numpy as np
import kagglehub
from sqlalchemy import create_engine
from flask import Flask, render_template, request, redirect, flash, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# IMPORT MODULAR PLUGINS
from rules_routes import rules_bp

app = Flask(__name__)
app.secret_key = "super_secret_meaningful_key"
# Database Connection Helper
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="kedge_db"
    )

# Custom template rendering filter to help interface payloads safely inside templates
@app.template_filter('from_json_filter_or_similar_if_any')
def from_json_filter(value):
    try:
        return json.loads(value)
    except:
        return {}

# Register our independent rule configuration route blueprint
app.register_blueprint(rules_bp)

def validate_password_policy(password):
    if len(password) < 4 or len(password) > 12:
        return False, "Password must be between 4 and 12 characters long."
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_+-]", password):
        return False, "Password must contain at least one special character."
    return True, "Success"

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username').strip()
        password = request.form.get('password')

        if not username or not password:
            flash("Please fill in all fields.", "failure")
            return render_template('login.html')

        conn = get_db_connection()
        cursor = conn.cursor()

        if action == 'register':
            is_valid, message = validate_password_policy(password)
            if not is_valid:
                flash(message, "failure")
                conn.close()
                return render_template('login.html')

            hashed_password = generate_password_hash(password)
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                cursor.execute(
                    "INSERT INTO users (username, password, date) VALUES (%s, %s, %s)",
                    (username, hashed_password, current_date)
                )
                conn.commit()
                flash("Registration successful! Please log in.", "success")
            except mysql.connector.Error:
                flash("Username already exists.", "failure")
            finally:
                conn.close()

        elif action == 'login':
            # Select both user_id and password
            cursor.execute("SELECT user_id, password FROM users WHERE username = %s", (username,))
            row = cursor.fetchone()
            conn.close()

            if row and check_password_hash(row[1], password):
                session['user'] = username
                session['user_id'] = row[0]  # Store user_id in session
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid username or password.", "failure")

    return render_template('login.html')
from flask import session, redirect, url_for, flash

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()  # Removes all session data
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login')) # Redirects to your login page

import io
import base64
import matplotlib
matplotlib.use('Agg') # Necessary for non-GUI backend in Flask
import matplotlib.pyplot as plt
import seaborn as sns

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please log in first.", "failure")
        return redirect(url_for('login'))

    try:
        engine = create_engine(f"mysql+mysqlconnector://root:{os.getenv('DB_PASSWORD')}@localhost:3306/kedge_db")

        # Set clean aesthetic style for Matplotlib
        sns.set_theme(style="whitegrid")
        palette = sns.color_palette("muted")

        # 1. Query Daily Bar Chart Data
        bar_query = """
            SELECT 
                DATE(alert_timestamp) AS alert_date,
                rule_name,
                COUNT(*) AS alert_count
            FROM alert_details
            WHERE alert_timestamp >= NOW() - INTERVAL 7 DAY
            GROUP BY DATE(alert_timestamp), rule_name
            ORDER BY alert_date ASC
        """
        df_bar = pd.read_sql(bar_query, con=engine)

        # Generate Bar Chart Image in Memory
        fig, ax = plt.subplots(figsize=(7, 4))
        if not df_bar.empty:
            df_bar['alert_date'] = pd.to_datetime(df_bar['alert_date'])
            full_date_range = pd.date_range(end=datetime.now().date(), periods=7)
            df_pivot = df_bar.pivot_table(index='alert_date', columns='rule_name', values='alert_count', fill_value=0)
            df_pivot = df_pivot.reindex(full_date_range, fill_value=0).reset_index()
            df_melted = df_pivot.melt(id_vars='index', var_name='rule_name', value_name='alert_count')
            df_melted.rename(columns={'index': 'alert_date'}, inplace=True)
            df_melted['alert_date'] = df_melted['alert_date'].dt.strftime('%m-%d')

            sns.barplot(data=df_melted, x='alert_date', y='alert_count', hue='rule_name', palette=palette, ax=ax)
            ax.set_title('Daily Alert Distribution (Last 7 Days)', fontsize=12, fontweight='bold', pad=15)
            ax.set_xlabel('Date', fontsize=10)
            ax.set_ylabel('Alert Count', fontsize=10)
            ax.legend(title='Rule Name', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        else:
            ax.text(0.5, 0.5, 'No alert data available', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        
        plt.tight_layout()
        img_bar = io.BytesIO()
        plt.savefig(img_bar, format='png', bbox_inches='tight', dpi=100)
        img_bar.seek(0)
        bar_url = base64.b64encode(img_bar.getvalue()).decode('utf8')
        plt.close(fig)

        # 2. Query Donut Chart Data
        donut_query = """
            SELECT 
                rule_name,
                COUNT(*) AS alert_count
            FROM alert_details
            WHERE alert_timestamp >= NOW() - INTERVAL 7 DAY
            GROUP BY rule_name
        """
        df_donut = pd.read_sql(donut_query, con=engine)

        # Generate Donut Chart Image in Memory
        fig, ax = plt.subplots(figsize=(5, 4))
        if not df_donut.empty:
            wedges, texts, autotexts = ax.pie(
                df_donut['alert_count'], 
                labels=df_donut['rule_name'], 
                autopct='%1.1f%%', 
                startangle=140, 
                colors=palette,
                wedgeprops=dict(width=0.4, edgecolor='w') # Creates the Donut hole
            )
            plt.setp(autotexts, size=8, weight="bold")
            plt.setp(texts, size=8)
            ax.set_title('1-Week Alert Proportion', fontsize=12, fontweight='bold', pad=15)
        else:
            ax.text(0.5, 0.5, 'No alerts recorded', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)

        plt.tight_layout()
        img_donut = io.BytesIO()
        plt.savefig(img_donut, format='png', bbox_inches='tight', dpi=100)
        img_donut.seek(0)
        donut_url = base64.b64encode(img_donut.getvalue()).decode('utf8')
        plt.close(fig)

    except Exception as e:
        bar_url = None
        donut_url = None

    return render_template('dashboard.html', bar_url=bar_url, donut_url=donut_url)

@app.route('/configuration')
def configuration():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    total_records = 0
    last_run_time = "Never"
    
    try:
        # Get total data count from transaction_details table
        cursor.execute("SELECT COUNT(*) AS total FROM transaction_details")
        res_count = cursor.fetchone()
        if res_count:
            total_records = res_count['total']
            
        # Get the latest execution timestamp when the rule engine worked
        cursor.execute("SELECT MAX(alert_timestamp) AS last_run FROM alert_details")
        res_run = cursor.fetchone()
        if res_run and res_run['last_run']:
            last_run_time = str(res_run['last_run'])
            
    except Exception as e:
        print(f"Error fetching telemetry metrics: {e}")
    finally:
        cursor.close()
        conn.close()

    return render_template('config.html', total_records=total_records, last_run_time=last_run_time)

@app.route('/check-engine-status')
def check_engine_status():
    if 'user' not in session:
        return {'status': 'unauthorized'}
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM system_settings WHERE setting_name = 'rule_engine'")
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if res and res['status'] == 'COMPLETED':
        return {'completed': True, 'message': 'All transactions processed. Rule Engine completed. Stopping scheduler as all data is processed.'}
    return {'completed': False}

# --- LIVE AUTOMATED KAGGLE DATA PULLING PIPELINE ROUTE ---
# ===== 1. ONLY CHANGE THIS BLOCK FOR NEW DATASET =====
DATASET_CONFIG = {
    'handle': 'valakhorasani/bank-transaction-dataset-for-fraud-detection', # 1. Put new dataset handle here
    'mapping': { # 2. Map kaggle columns to YOUR columns here
        'account_number': 'acn',
        'transaction_amount': 'txn_amt',
        'current_balance': 'closing_bal',
        'transaction_date': 'aod',
        'transaction_type': 'dr_cr'
    }
}
# =====================================================

@app.route('/toggle-data', methods=['POST'])
def toggle_data():
    if 'user' not in session:
        return redirect(url_for('login'))

    is_on = request.form.get('data_pulling') == 'on' or 'data_pull' in request.form
    session['data_pulling'] = is_on

    if is_on:
        try:
            import random
            from datetime import datetime, timedelta

            os.environ['KAGGLE_USERNAME'] = os.getenv('KAGGLE_USERNAME')
            os.environ['KAGGLE_KEY'] = os.getenv('KAGGLE_KEY')

            dataset_handle = DATASET_CONFIG['handle']
            mapping = DATASET_CONFIG['mapping']

            downloaded_path = kagglehub.dataset_download(dataset_handle)
            files = os.listdir(downloaded_path)
            target_csv = [f for f in files if f.endswith('.csv')][0]
            csv_full_path = os.path.join(downloaded_path, target_csv)

            raw_df = pd.read_csv(csv_full_path)
            
            # Let's define fewer base rows so we can expand them into multiple transactions per account
            base_subset = raw_df.head(400).copy()
            base_subset.rename(columns=mapping, inplace=True)

            channels = ['Mobile', 'ATM', 'NetBanking', 'UPI', 'Branch', 'POS']
            narration_options = ['GST Payment', 'Premature FD withdrawal', 'Salary Credit', 'NEFT Transaction', 'Interest Credit']
            occupations_list = ['Engineer', 'Doctor', 'Business Owner', 'Manager', 'Teacher', 'Consultant', 'Student', 'Retired']

            def generate_turnover(occ):
                if occ == 'Student': return np.random.uniform(1000, 100000)
                elif occ == 'Retired': return np.random.uniform(5000, 300000)
                elif occ == 'Teacher': return np.random.uniform(120000, 600000)
                elif occ == 'Engineer': return np.random.uniform(300000, 900000)
                elif occ == 'Doctor': return np.random.uniform(500000, 2000000)
                elif occ == 'Business Owner': return np.random.uniform(1000000, 5000000)
                else: return np.random.uniform(250000, 800000)

            expanded_rows = []
            start_date_limit = datetime.now() - timedelta(days=5*365)

            # Generate multiple transactions for each account
            for index, row in base_subset.iterrows():
                acn = f"ACN{index}"
                cid = f"CID{index}"
                # MIXED AOD: Ensures we get both brand new and older accounts
                if random.random() < 0.40:
                    aod = datetime.now() - timedelta(days=random.randint(0, 25))
                else:
                    aod = start_date_limit + timedelta(days=random.randint(30, 4*365))
                occupation = np.random.choice(occupations_list)
                turnover = round(generate_turnover(occupation), 2)
                
                # Decide how many transactions this account will have (e.g., between 1 to 5 transactions)
                num_transactions = random.randint(1, 5)
                closing_bal = round(np.random.uniform(5000.0, 500000.0), 2)

                for t in range(num_transactions):
                    # Each subsequent transaction happens a few days/months after account opening or previous txn
                    txn_date = aod + timedelta(days=random.randint(1, 300))
                    dr_cr = np.random.choice(['DR', 'CR'], p=[0.55, 0.45])
                    txn_amt = round(np.random.uniform(500.0, 300000.0), 2)
                    
                    if dr_cr == 'CR':
                        closing_bal += txn_amt
                    else:
                        closing_bal = max(100.0, closing_bal - txn_amt)

                    channel = np.random.choice(channels)
                    narration = np.random.choice(narration_options)

                    expanded_rows.append({
                        'acn': acn,
                        'cid': cid,
                        'aod': aod.strftime('%Y-%m-%d'),
                        'dr_cr': dr_cr,
                        'txn_amt': txn_amt,
                        'closing_bal': round(closing_bal, 2),
                        'channel': channel,
                        'narration': narration,
                        'occupation': occupation,
                        'turnover': turnover
                    })

            final_df = pd.DataFrame(expanded_rows)

            conn = get_db_connection()
            cursor = conn.cursor()
            
            # TRUNCATE clears table and resets txn_id back to 1 automatically
            cursor.execute("TRUNCATE TABLE transaction_details")
            
            for _, row in final_df.iterrows():
                sql = """INSERT INTO transaction_details 
                         (acn, cid, aod, dr_cr, txn_amt, closing_bal, channel, narration, occupation, turnover) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, tuple(row))
            
            conn.commit()
            conn.close()
            flash(f"Data pulled successfully with multi-transaction histories!", "success")

        except Exception as e:
            flash(f"Data pulling failed: {e}", "failure")
    else:
        flash("Data deactivated.", "success")

    return render_template('config.html')

from engine import run_rule_engine # Import the new engine

import subprocess
import sys
# ... your other imports ...

# Global variable to track the engine process
engine_process = None

@app.route('/toggle-rules', methods=['POST'])
def toggle_rules():
    global engine_process
    if 'user' not in session:
        return redirect(url_for('login'))
        
    is_on = request.form.get('rule_engine') == 'on' or 'rule_engine' in request.form
    new_status = 'ON' if is_on else 'OFF'
    
    # Update Database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE system_settings SET status = %s WHERE setting_name = 'rule_engine'", (new_status,))
    conn.commit()
    cursor.close()
    conn.close()
    
    # Logic to start/stop engine.py process
    if new_status == 'ON':
        # Check if process is already running to avoid duplicates
        if engine_process is None or engine_process.poll() is not None:
            # Starts engine.py in the background
            engine_process = subprocess.Popen([sys.executable, "engine.py"])
    else:
        # Terminate the process if it exists
        if engine_process is not None:
            engine_process.terminate()
            engine_process = None
    
    session['rule_engine'] = is_on
    flash(f"Rule Engine has been set to {new_status}.", "success")
    return render_template('config.html')
@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    tab = request.args.get('tab', 'summary') # Default to alert summary tab
    engine = create_engine(f"mysql+mysqlconnector://root:{os.getenv('DB_PASSWORD')}@localhost:3306/kedge_db")
    
    summary_data = []
    full_alerts = []
    from_date = request.form.get('from_date', '')
    to_date = request.form.get('to_date', '')

    try:
        if tab == 'summary':
            if request.method == 'POST' and from_date and to_date:
                summary_query = """
                    SELECT rule_name, COUNT(*) AS trigger_count
                    FROM alert_details
                    WHERE DATE(alert_timestamp) BETWEEN %s AND %s
                    GROUP BY rule_name
                """
                summary_df = pd.read_sql(summary_query, con=engine, params=(from_date, to_date))
            else:
                # Default view showing all-time summary or recent summary if no dates chosen
                summary_query = """
                    SELECT rule_name, COUNT(*) AS trigger_count
                    FROM alert_details
                    GROUP BY rule_name
                """
                summary_df = pd.read_sql(summary_query, con=engine)
            
            summary_data = summary_df.to_dict(orient='records')

        elif tab == 'full':
            full_query = "SELECT * FROM alert_details ORDER BY alert_timestamp DESC"
            full_df = pd.read_sql(full_query, con=engine)
            full_alerts = full_df.to_dict(orient='records')

    except Exception as e:
        flash(f"Error loading report data: {e}", "failure")

    return render_template('report.html', 
                           active_tab=tab, 
                           summary_data=summary_data, 
                           full_alerts=full_alerts,
                           from_date=from_date,
                           to_date=to_date)

@app.route('/forgot-password')
def forgot_password():
    return "<h2 style='font-family:sans-serif; text-align:center; margin-top:50px;'>Password reset link has been simulated and sent.</h2>"

if __name__ == '__main__':
    app.run(debug=True)