import os
from pathlib import Path
from plot import generate_html

def main():

    record_dir = "./rag_records"
    task_name = "fixed_task"  
    
    try:

        steps_file = Path(record_dir) / "steps.json"
        if not steps_file.exists():
            print(f"❌ steps.json not found in {record_dir}")
            return
            

        html_path = generate_html(
            run_dir=record_dir,
            model="Mobile_Agent_4o",
            run="",
            task=task_name
        )
        print(f"✅ HTML report generated successfully at: {html_path}")
        
    except Exception as e:
        print(f"❌ Error generating HTML report: {str(e)}")

if __name__ == "__main__":
    main() 