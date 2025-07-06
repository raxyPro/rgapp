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


def getICDatav1(data):
    """
    Parses the intro card data and returns a dictionary.
    If the data is empty, it returns an empty dictionary.
    """
    import json
    try:
        return json.loads(data) if data else {}
    except json.JSONDecodeError:
        return {}
