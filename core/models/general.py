from django.db import models


class GeneralSettings(models.Model):
    MODEL_CHOICES = [("gpt-5.1", "GPT 5.1"), ("gemini-3", "Gemini 3")]
    llm_model = models.CharField(
        max_length=100, choices=MODEL_CHOICES, default="gpt-5.1"
    )
