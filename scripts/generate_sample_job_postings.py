import csv
from datetime import datetime, timedelta
from pathlib import Path

TRAIN_PATH = Path(__file__).resolve().parents[1] / "data" / "job_postings_training.csv"
PROD_PATH = Path(__file__).resolve().parents[1] / "data" / "job_postings_production.csv"

TRAIN_ROWS = [
    {
        "id": f"train_{i+1:03d}",
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "required_skills": skills,
        "posted_date": (datetime(2025, 12, 1) + timedelta(days=i)).date().isoformat(),
        "source": "kaggle" if i % 2 == 0 else "linkedin",
        "remote_status": remote_status,
        "role_type": role_type,
    }
    for i, (title, company, location, description, salary_min, salary_max, skills, remote_status, role_type) in enumerate([
        ("Data Scientist", "DataCorp", "New York, NY", "Modeling and analytics work.", 110000, 140000, "Python;SQL;Machine Learning", "remote", "Data Science"),
        ("Backend Engineer", "Buildify", "San Francisco, CA", "API and infrastructure development.", 130000, 160000, "Python;Docker;Kubernetes", "onsite", "Engineering"),
        ("Machine Learning Engineer", "NeuroAI", "Austin, TX", "Training and deploying models.", 125000, 155000, "Python;PyTorch;SQL", "remote", "Engineering"),
        ("DevOps Engineer", "CloudWay", "Seattle, WA", "Pipeline automation and monitoring.", 120000, 145000, "Terraform;Kubernetes;Docker", "onsite", "DevOps"),
        ("Data Analyst", "Insightful", "Boston, MA", "Business reporting and dashboards.", 90000, 115000, "SQL;Tableau;Excel", "hybrid", "Data"),
        ("Full Stack Developer", "RapidWeb", "Denver, CO", "Web application development.", 115000, 145000, "JavaScript;React;Node.js", "remote", "Engineering"),
        ("Product Manager", "LaunchPad", "Chicago, IL", "Roadmap and stakeholder coordination.", 105000, 130000, "Agile;Communication;Leadership", "onsite", "Product"),
        ("Data Engineer", "Streamline", "New York, NY", "ETL and data lake management.", 125000, 150000, "Python;Spark;SQL", "remote", "Engineering"),
        ("AI Researcher", "InnovateAI", "Palo Alto, CA", "Experimental model research.", 135000, 170000, "Python;TensorFlow;Research", "hybrid", "Research"),
        ("Cloud Architect", "SkyScale", "Miami, FL", "Cloud design and security.", 140000, 175000, "AWS;Terraform;Security", "onsite", "Architecture"),
    ])
]

PROD_ROWS = [
    {
        "id": f"prod_{i+1:03d}",
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "required_skills": skills,
        "posted_date": (datetime(2026, 1, 10) + timedelta(days=i)).date().isoformat(),
        "source": "kaggle" if i % 2 == 1 else "linkedin",
        "remote_status": remote_status,
        "role_type": role_type,
    }
    for i, (title, company, location, description, salary_min, salary_max, skills, remote_status, role_type) in enumerate([
        ("Data Scientist", "DataCorp", "New York, NY", "Modeling and analytics work.", 115000, 145000, "Python;SQL;Machine Learning", "remote", "Data Science"),
        ("Backend Engineer", "Buildify", "San Francisco, CA", "API and infrastructure development.", 135000, 165000, "Python;Docker;Kubernetes", "remote", "Engineering"),
        ("Machine Learning Engineer", "NeuroAI", "Austin, TX", "Training and deploying models.", 128000, 160000, "Python;PyTorch;SQL", "remote", "Engineering"),
        ("DevOps Engineer", "CloudWay", "Seattle, WA", "Pipeline automation and monitoring.", 122000, 148000, "Terraform;Kubernetes;Docker", "onsite", "DevOps"),
        ("Data Analyst", "Insightful", "Boston, MA", "Business reporting and dashboards.", 92000, 118000, "SQL;Tableau;Excel", "hybrid", "Data"),
        ("Full Stack Developer", "RapidWeb", "Denver, CO", "Web application development.", 117000, 148000, "JavaScript;React;Node.js", "remote", "Engineering"),
        ("Product Manager", "LaunchPad", "Chicago, IL", "Roadmap and stakeholder coordination.", 108000, 133000, "Agile;Communication;Leadership", "remote", "Product"),
        ("Data Engineer", "Streamline", "New York, NY", "ETL and data lake management.", 128000, 155000, "Python;Spark;SQL", "remote", "Engineering"),
        ("AI Researcher", "InnovateAI", "Palo Alto, CA", "Experimental model research.", 138000, 175000, "Python;TensorFlow;Research", "hybrid", "Research"),
        ("Cloud Architect", "SkyScale", "Miami, FL", "Cloud design and security.", 142000, 178000, "AWS;Terraform;Security", "remote", "Architecture"),
    ])
]

COLUMNS = [
    "id",
    "title",
    "company",
    "location",
    "description",
    "salary_min",
    "salary_max",
    "required_skills",
    "posted_date",
    "source",
    "remote_status",
    "role_type",
]


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    write_csv(TRAIN_PATH, TRAIN_ROWS)
    write_csv(PROD_PATH, PROD_ROWS)
    print(f"Wrote {len(TRAIN_ROWS)} training rows to {TRAIN_PATH}")
    print(f"Wrote {len(PROD_ROWS)} production rows to {PROD_PATH}")


if __name__ == "__main__":
    main()
