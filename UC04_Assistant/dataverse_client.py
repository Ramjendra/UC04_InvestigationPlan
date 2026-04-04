import os
import requests
from dotenv import load_dotenv

load_dotenv()

class DataverseClient:
    def __init__(self):
        self.org_url = os.getenv("DATAVERSE_ORG_URL")
        self.token = os.getenv("DATAVERSE_TOKEN")

    def query(self, entity_name, **kwargs):
        if entity_name == "incidents":
            return [{
                "ticketnumber": "BRI-26-11514",
                "title": "Unauthorized Access - APAC Region",
                "description": "Alleged unauthorized access to project documents via AI co-pilot website.",
                "createdon": "2026-02-22T12:00:00Z",
                "statuscode": 1
            }]
        return []

    def get_investigation_plan(self, case_id):
        return {
            "attorney_comments": "Initial review completed on 2/22/2026. Case appears to involve a potential data breach or account takeover. Cross-referencing with IT security logs is required.",
            "summary_of_allegations": """The text describes a situation where a person was working on a pre-adoption project plan to help individuals manage expenses during pre-adoption. While trying to access her saved documents on the AI co-pilot website, she was unexpectedly logged out. When she attempted to log back in, the website indicated that her login details were incorrect and showed a different email address (ye@student.lns.edu) and a phone number ending in 11, which she did not recognize. She could not verify these details because the system automatically logged her out without warning. She had already entered all her project information and suspects that someone may have stolen her plan. She is requesting an investigation into the AI co-pilot website because she can no longer sign in or access her drafted project details.""",
            "questions_to_be_answered": [
                {"Question Number": 1, "Question": "What was the exact time of the unexpected logout?"},
                {"Question Number": 2, "Question": "Is 'ye@student.lns.edu' a known alias or internal account?"},
                {"Question Number": 3, "Question": "Are there any logs showing access from unknown IP addresses?"}
            ],
            "proposed_investigative_steps": [
                {"Step Number": 1, "Investigation Step": "Review AI Co-pilot Access Logs", "Team": "IT security", "Status": "In Progress", "Notes": "Check for IP mismatches."},
                {"Step Number": 2, "Investigation Step": "Identify Investigation Stages", "Team": "Legal", "Status": "Completed", "Notes": "CILA framework applied."},
                {"Step Number": 3, "Investigation Step": "Determine Required Documents", "Team": "Compliance", "Status": "Pending", "Notes": "Standard evidence matrix."}
            ]
        }
