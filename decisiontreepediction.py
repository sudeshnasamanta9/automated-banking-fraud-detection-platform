import pickle
import pandas as pd
import time
import os
from dotenv import load_dotenv
import mysql.connector
from datetime import datetime

load_dotenv()

# 1. Database Connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="kedge_db"
    )

# 2. Rule Engine: Logic for Rule 2 & 3
def check_custom_rules(row):
    # Rule 2: High value credit in new account
    # Conditions: AOD < 90, Narration != premature, Cumulative Credit > 500,000
    rule2 = (row['aod_days'] < 90 and 
             "premature" not in str(row['narration']).lower() and 
             row['cum_credit'] > 500000)
    
    # Rule 3: New account followed by ATM withdrawal
    # Conditions: AOD < 30, Cum Credit > 50,000, Cum Debit > 40,000, Channel = 'atm'
    rule3 = (row['aod_days'] < 30 and 
             row['cum_credit'] > 50000 and 
             row['cum_debit'] > 40000 and 
             str(row['channel']).lower() == 'atm')
    
    return rule2 or rule3

# 3. Load Model
filename = r"D:\6th Sem\InternShip_26\Data\gst_refund.pickle"
loaded_model = pickle.load(open(filename, "rb"))

# 4. Fetch and Prepare Data
conn = get_db_connection()
df = pd.read_sql("SELECT * FROM transaction_details", conn)
conn.close()

# Calculate AOD and Cumulative amounts
current_date = datetime.now()
df['aod_days'] = (current_date - pd.to_datetime(df['aod'])).dt.days

# Calculate running totals per account
df = df.sort_values(['acn', 'aod'])
df['cum_credit'] = df.apply(lambda x: x['txn_amt'] if x['dr_cr'] == 'CR' else 0, axis=1).groupby(df['acn']).cumsum()
df['cum_debit'] = df.apply(lambda x: x['txn_amt'] if x['dr_cr'] == 'DR' else 0, axis=1).groupby(df['acn']).cumsum()

# 5. Prediction Loop
safe_count, suspicious_count = 0, 0
start_ts = time.time()

for index, row in df.iterrows():
    # ML Features
    narration_feat = 1 if "gst" in str(row['narration']).lower() else 0
    dr_cr_feat = 1 if str(row['dr_cr']).upper() == 'CR' else 0
    input_df = pd.DataFrame([[row['aod_days'], narration_feat, dr_cr_feat]], 
                            columns=['aod', 'narration', 'dr_cr'])
    
    ml_result = loaded_model.predict(input_df)[0]
    rule_breach = check_custom_rules(row)
    # ADD THIS LINE TO DEBUG:
    if rule_breach:
        print(f"DEBUG: Transaction {index} triggered a custom rule!")
    
    if ml_result == 1 or rule_breach:
        suspicious_count += 1
        status = "SUSPICIOUS"
    else:
        safe_count += 1
        status = "SAFE"
    
    print(f"Transaction {index} (Acc: {row['acn']}): {status}")

# 6. Summary
print(f"\nFinal Summary: SAFE: {safe_count}, SUSPICIOUS: {suspicious_count}")