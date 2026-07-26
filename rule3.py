import pandas as pd
import pickle
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree

# 1. Load your CSV file
# Columns: aod, cumulative_credit, cumulative_debit, channel, output
df = pd.read_csv(r"D:\6th Sem\InternShip_26\Data\rule3_data.csv")

# 2. Split data: Features (first 4 cols) and Target (last col)
X = df.iloc[:, 0:-1]
y = df.iloc[:, -1]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Create and Train the Classifier
clf = DecisionTreeClassifier(random_state=42)
clf.fit(X_train, y_train)

# 4. Save the model as a pickle file
filename = r"D:\6th Sem\InternShip_26\Data\rule3_atm_withdrawal.pickle"
with open(filename, "wb") as f:
    pickle.dump(clf, f)

print(f"Rule 3 Model saved to {filename}")

# 5. Visualize the tree
plt.figure(figsize=(14, 8))
plot_tree(
    clf, 
    filled=True, 
    feature_names=["aod", "cumulative_credit", "cumulative_debit", "channel"], 
    class_names=["Safe", "Suspicious"], 
    rounded=True
)
plt.title("Decision Tree Visualization - Rule 3 (ATM Withdrawal)")
plt.show()