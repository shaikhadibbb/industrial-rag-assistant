import random
import os
from locust import HttpUser, task, between

QUESTIONS = [
    "What should be done if the compressor's high-pressure warning transducer value approaches the limit?",
    "What is the consequence of internal corrosion in a compressed air receiver vessel?",
    "Where are soft start starters usually positioned and why?",
    "How often must internal condensing water be drained from an air receiver vessel?",
    "What is an open cooling system without circulating water and how is it supplied?",
    "What is the standard regulation method for compressors with a capacity greater than 5 kW?",
    "What troubleshooting value does a compressor's integrated memory storage provide?",
    "What is the hazard of running a corroded air vessel without a daily drain routine?"
]

class MaintenanceTechnician(HttpUser):
    wait_time = between(1, 5) # Simulates a 1-5 second thinking delay between tasks

    def on_start(self):
        # Configure X-API-Key header if set in environment
        self.api_key = os.getenv("API_KEY", "")
        self.headers = {}
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key

    @task(3)
    def query_rag(self):
        question = random.choice(QUESTIONS)
        self.client.post(
            "/query", 
            json={"question": question, "session_id": "locust_session"},
            headers=self.headers
        )

    @task(1)
    def check_health(self):
        self.client.get("/health")
