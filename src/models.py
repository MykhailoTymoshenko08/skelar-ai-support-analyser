from pydantic import BaseModel
from pydantic import Field
from enum import Enum

class Intent(str, Enum):
    PAYMENT_PROBLEM = "Payment problem"
    TECH_ERROR = "Technical errors"
    ACCOUNT_ACCESS = "Account access"
    REFUND = "Refund"
    TARIFF_QUESTION = "Tariff question"
    OTHER = "Other"

class Satisfaction(str, Enum):
    SATISFIED = "Satisfied"
    NEUTRAL = "Neutral"
    UNSATISFIED = "Unsatisfied"

class AgentMistake(str, Enum):
    IGNORED_QUESTION = "Ignored question"
    INCORRECT_INFO = "Incorrect info"
    RUDE_TONE = "Rude tone"
    NO_RESOLUTION = "No resolution"
    UNNECESSARY_ESCALATION = "Unnecessary escalation"

class ChatStats(BaseModel):
    id: int
    intent: Intent
    satis: Satisfaction
    quality_score: int = Field(ge=1, le=5)
    agent_mistake: set[AgentMistake] | None

class Result(BaseModel):
    statsList: list[ChatStats]

if __name__ == '__main__':
    chat1 = ChatStats(
            id = 0,
            intent = Intent.ACCOUNT_ACCESS,
            satis = Satisfaction.NEUTRAL,
            quality_score = 4,
            agent_mistake = {AgentMistake.RUDE_TONE, AgentMistake.INCORRECT_INFO},
        )

    chat2 = ChatStats(
            id = 1,
            intent = Intent.OTHER,
            satis = Satisfaction.SATISFIED,
            quality_score = 1,
            agent_mistake = None,
        )

    result = Result(
        statsList = [chat1, chat2]
    )
    
    print(
        result.model_dump_json(indent=2)
    )
