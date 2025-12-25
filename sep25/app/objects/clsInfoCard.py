from flask import json


pf_data_v1 = """
{
    "name": " ",
    "role": " ",
    "email": " ",
    "organization": " ",
    "website": " ",
    "mobile": " ",
    "skills": []
    "services": []
"""


def getICDatav1(data_in_db):
    """
    Parses the intro card data and returns a dictionary.
    If the data is empty, it returns an empty dictionary.
    """
    # Default template
    pf_template = {
        "name": " ",
        "role": " ",
        "email": " ",
        "organization": " ",
        "website": " ",
        "mobile": " ",
        "skills": [],
        "services": []
    }

    try:
        db_data = json.loads(data_in_db) if data_in_db else {}
    except json.JSONDecodeError:
        db_data = {}

    # Map db_data to pf_template, keeping blanks/defaults if missing
    result = {}
    for key in pf_template:
        result[key] = db_data.get(key, pf_template[key])
    return result
    
    if __name__ == "__main__":
        data_in_db = """{
   "name": "Rajat Sharma",
   "role": "Agile Project Manager",
   "email": "rajat.sharma@raygrowcs.com",
   "organization": "RayGrow Connsulting",
   "website": "www.raygrowcs.com",
   "mobile": "+918138926888",
   "telephone": "+911202668998",
   "services": [
     "Project Management: Planning, Resourcing, Execution",
     "Team Management: Building, Leading, and Motivating Teams",
     "Program Management: Coordinating Multiple Projects and Stakeholders",
     "Agile Coaching: Guiding Teams in Agile Principles and Practices",
     "Agile Setup: Implementing Agile Frameworks and Processes",
     "Software Development: Designing, Coding, and Delivering Applications"
   ]
 }"""