import pandas as pd
import pickle
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree

# 1. Load your CSV file
df = pd.read_csv(r"D:\6th Sem\InternShip_26\Data\rule1_gst_refund.csv")

# 2. Split data: Features (first 3 cols) and Target (last col)
X = df.iloc[:, 0:-1]
y = df.iloc[:, -1]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Create and Train the Classifier
clf = DecisionTreeClassifier(random_state=42)
clf.fit(X_train, y_train)

# 4. Save the model
filename = r"D:\6th Sem\InternShip_26\Data\rule1_gst_refund.pickle"
with open(filename, "wb") as f:
    pickle.dump(clf, f)

print(f"Model saved to {filename}")

# 5. Visualize the tree
plt.figure(figsize=(12, 8))
plot_tree(
    clf, 
    filled=True, 
    feature_names=["AOD", "narration", "dr_cr"], 
    class_names=["Safe", "Suspicious"], # This labels your outcomes
    rounded=True
)
plt.title("Decision Tree: GST Refund Rule")
plt.show()