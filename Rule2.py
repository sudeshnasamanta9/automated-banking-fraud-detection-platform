import pandas as pd
import pickle
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree

# 1. Load your CSV file
# Ensure columns are ordered: aod, narration, cumulative_credit, output
df = pd.read_csv(r"D:\6th Sem\InternShip_26\Data\rule_2_High.csv")

# 2. Split data: Features (first 3 cols) and Target (last col)
X = df.iloc[:, 0:-1]
y = df.iloc[:, -1]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Create and Train the Classifier
clf = DecisionTreeClassifier(random_state=42)
clf.fit(X_train, y_train)

# 4. Save the model as a pickle file
filename = r"D:\6th Sem\InternShip_26\Data\rule2_high_value.pickle"
with open(filename, "wb") as f:
    pickle.dump(clf, f)

print(f"Rule 2 Model saved to {filename}")

# 5. Visualize the tree using matplotlib (Consistent with Rule 1)
plt.figure(figsize=(12, 8))
plot_tree(
    clf, 
    filled=True, 
    feature_names=["aod", "narration", "cumulative_credit"], 
    class_names=["Safe", "Suspicious"], 
    rounded=True
)
plt.title("Decision Tree Visualization - Rule 2")
plt.show()