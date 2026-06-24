import os
import sys
import json
import csv
import time
import pandas as pd
from datetime import datetime

# Ensure the root directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the pipeline from app.py
from app import run_full_pipeline

TEST_BANK_PATH = "tests/test_question_bank.csv"
RESULTS_PATH = "tests/test_results.csv"

def run_evaluation():
    print(f"Loading test bank from {TEST_BANK_PATH}...")
    if not os.path.exists(TEST_BANK_PATH):
        print("Error: Test bank not found.")
        return

    test_df = pd.read_csv(TEST_BANK_PATH)
    results = []

    print(f"Starting evaluation of {len(test_df)} questions...")
    
    for index, row in test_df.iterrows():
        qid = row['QuestionID']
        category = row['Category']
        question = row['Question']
        expected_pattern = row['ExpectedSQLPattern']
        is_safety = row['IsSafetyTest']
        
        print(f"[{qid}/50] Processing: {question[:50]}...")
        
        start_time = time.time()
        try:
            # Run the pipeline (empty history for independent tests)
            res = run_full_pipeline(question, [])
            elapsed = time.time() - start_time
            
            # Basic pass/fail logic
            # For safety tests, blocked=True is a PASS
            # For normal tests, error="" is a PASS
            status = "FAIL"
            if is_safety:
                if res.get('blocked'):
                    status = "PASS (Correctly Blocked)"
                else:
                    status = "FAIL (Safety Breach)"
            else:
                if res.get('error'):
                    status = f"FAIL ({res.get('error')})"
                elif res.get('sql'):
                    status = "PASS"
                else:
                    status = "FAIL (No SQL generated)"

            results.append({
                "QuestionID": qid,
                "Category": category,
                "Question": question,
                "Status": status,
                "GeneratedSQL": res.get('sql', ""),
                "Explanation": res.get('explanation', ""),
                "Error": res.get('error', ""),
                "Blocked": res.get('blocked', False),
                "ElapsedSeconds": round(elapsed, 2)
            })
            
        except Exception as e:
            print(f"Error on question {qid}: {e}")
            results.append({
                "QuestionID": qid,
                "Category": category,
                "Question": question,
                "Status": f"CRASH ({str(e)})",
                "GeneratedSQL": "",
                "Explanation": "",
                "Error": str(e),
                "Blocked": False,
                "ElapsedSeconds": round(time.time() - start_time, 2)
            })
        
        # Rate limit protection: Sleep for 12 seconds between questions
        time.sleep(12)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(RESULTS_PATH, index=False)
    print(f"\nEvaluation complete! Results saved to {RESULTS_PATH}")
    
    # Summary
    pass_count = len(results_df[results_df['Status'].str.contains("PASS")])
    fail_count = len(results_df) - pass_count
    accuracy = (pass_count / len(results_df)) * 100
    print(f"Summary: {pass_count} Passed, {fail_count} Failed. Accuracy: {accuracy:.1f}%")

if __name__ == "__main__":
    run_evaluation()
