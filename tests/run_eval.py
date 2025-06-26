#!/usr/bin/env python3
"""
Simple script to run evaluations on existing research reports
"""

import os
import glob
from pathlib import Path
from evaluator import ResearchReportEvaluator
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

def find_reports(directory="./reports"):
    """Find all research report markdown files"""
    pattern = os.path.join(directory, "*.md")
    return glob.glob(pattern)

def main():
    """Main function to run evaluations on existing reports"""
    
    # Find all research reports
    reports = find_reports()
    
    if not reports:
        print("No research reports found in ./reports directory")
        return
    
    # Display available reports with numbers
    print("Available research reports:")
    print("-" * 50)
    for i, report in enumerate(reports, 1):
        filename = os.path.basename(report)
        print(f"{i}. {filename}")
    print("-" * 50)
    
    # Ask user which report to evaluate
    choice = input("Enter report number to evaluate: ").strip()
    
    try:
        index = int(choice) - 1
        if 0 <= index < len(reports):
            selected_report = reports[index]
            print(f"Evaluating: {os.path.basename(selected_report)}")
        else:
            print("Invalid report number")
            return
    except (ValueError, IndexError):
        print("Invalid input. Please enter a valid number.")
        return
    
    # Initialize evaluator
    evaluator = ResearchReportEvaluator()
    
    # Evaluate the selected report
    try:
        result = evaluator.evaluate_report(selected_report)
        
        # Save evaluation
        output_path = evaluator.save_evaluation(result)
        print(f"Evaluation saved to: {output_path}")
        
    except Exception as e:
        print(f"Error during evaluation: {e}")

if __name__ == "__main__":
    main() 