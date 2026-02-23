import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


arcee_ai = "arcee-ai/trinity-large-preview:free"
step_fun = "stepfun/step-3.5-flash:free"
open_ai = "openai/gpt-oss-20b:free"

default_model = arcee_ai

class intent:
    payment_problem = "payment_problem"
    tech_error = "tech_error"
    account_access = "account_access"
    tariff = "tariff"
    refund = "refund"
    other = "other"

intent_choices = [
    intent.payment_problem,
    intent.tech_error, 
    intent.account_access,
    intent.tariff,
    intent.refund,
    intent.other
]

hidden_dissatisfaction_keywords = [
    "fine i guess",
    "whatever",
    "ok i suppose",
    "doesn't matter",
    "as you wish",
    "if you say so",
    "never mind",
    "forget it",
    "whatever you think",
    "i don't care anymore"
]

dissatisfaction_threshold = 0.7

openrouter_base_url = "https://openrouter.ai/api/v1"
openrouter_api_base = openrouter_base_url