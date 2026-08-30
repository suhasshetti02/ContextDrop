import json
import requests
import sys

API_URL = "http://localhost:8000/api"
INTERNAL_API_KEY = "default-internal-secret-key-12345"

def evaluate_retrieval(slug, k=5):
    with open("questions.json", "r") as f:
        questions = json.load(f)

    correct = 0
    total = len(questions)

    for item in questions:
        question = item['question']
        expected_snippet = item['expected_text_snippet'].lower()
        
        try:
            res = requests.post(
                f"{API_URL}/capsules/{slug}/search",
                json={"question": question},
                headers={"Authorization": f"Bearer {INTERNAL_API_KEY}"}
            )
            res.raise_for_status()
            chunks = res.json().get('chunks', [])
            
            # Check if expected snippet is in top K
            found = False
            for chunk in chunks[:k]:
                if expected_snippet in chunk['text'].lower():
                    found = True
                    break
                    
            if found:
                correct += 1
            else:
                print(f"Failed Recall@{k} for: {question}")
        except Exception as e:
            print(f"Error evaluating '{question}': {e}")
            
    recall = correct / total if total > 0 else 0
    print(f"Recall@{k}: {recall:.2f} ({correct}/{total})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python evaluate.py <capsule_slug>")
        sys.exit(1)
    evaluate_retrieval(sys.argv[1])
