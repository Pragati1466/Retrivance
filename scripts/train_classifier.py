import json
import pickle
import random
from pathlib import Path
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, precision_recall_curve, auc


def load_training_data(poisoned_path: str = "data/benchmark/poisoned_corpus.jsonl",
                       clean_path: str = "data/benchmark/clean_corpus.jsonl") -> Tuple[List[str], List[int]]:
    """Loads and balances training data."""
    texts = []
    labels = []
    
    # Load poisoned samples (label 1)
    with open(poisoned_path, "r") as f:
        for line in f:
            data = json.loads(line)
            texts.append(data["text"])
            labels.append(1)
    
    # Load clean samples (label 0)
    with open(clean_path, "r") as f:
        for line in f:
            data = json.loads(line)
            texts.append(data["text"])
            labels.append(0)
    
    # Balance the dataset
    min_count = min(labels.count(0), labels.count(1))
    clean_indices = [i for i, label in enumerate(labels) if label == 0]
    poison_indices = [i for i, label in enumerate(labels) if label == 1]
    
    random.seed(42)
    clean_indices = random.sample(clean_indices, min_count)
    poison_indices = random.sample(poison_indices, min_count)
    
    balanced_texts = [texts[i] for i in clean_indices + poison_indices]
    balanced_labels = [labels[i] for i in clean_indices + poison_indices]
    
    return balanced_texts, balanced_labels


def train_classifier():
    """Trains TF-IDF + LogisticRegression classifier."""
    print("Loading training data...")
    texts, labels = load_training_data()
    print(f"Loaded {len(texts)} samples ({sum(labels)} poisoned, {len(labels) - sum(labels)} clean)")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42, stratify=labels)
    
    # TF-IDF vectorization
    print("Training TF-IDF vectorizer...")
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=2)
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)
    
    # Train classifier
    print("Training LogisticRegression classifier...")
    clf = LogisticRegression(random_state=42, max_iter=1000, class_weight='balanced')
    clf.fit(X_train_tfidf, y_train)
    
    # Evaluate
    y_pred = clf.predict(X_test_tfidf)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Clean', 'Poisoned']))
    
    # Calculate PR-AUC
    y_scores = clf.predict_proba(X_test_tfidf)[:, 1]
    precision, recall, _ = precision_recall_curve(y_test, y_scores)
    pr_auc = auc(recall, precision)
    print(f"PR-AUC: {pr_auc:.4f}")
    
    # Save model
    output_dir = Path("models")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "injection_clf.pkl", "wb") as f:
        pickle.dump({"vectorizer": vectorizer, "classifier": clf}, f)
    
    print(f"\nModel saved to {output_dir / 'injection_clf.pkl'}")
    
    # Print threshold analysis
    print("\nThreshold Analysis:")
    for threshold in [0.3, 0.5, 0.7, 0.9]:
        y_pred_thresh = (y_scores >= threshold).astype(int)
        precision = sum((y_pred_thresh == 1) & (y_test == 1)) / max(1, sum(y_pred_thresh == 1))
        recall = sum((y_pred_thresh == 1) & (y_test == 1)) / max(1, sum(y_test == 1))
        print(f"Threshold {threshold}: Precision={precision:.3f}, Recall={recall:.3f}")


if __name__ == "__main__":
    train_classifier()
