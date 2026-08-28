"""Abstract Base Classes for Fraud Detection Rules."""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from services.fraud_service.app.schemas.fraud import FraudCheckRequest


class RuleEvaluationResult(BaseModel):
    rule_name: str
    score_increment: float
    reason: str | None = None
    triggered: bool = False


class BaseFraudRule(ABC):
    """Abstract interface for any deterministic or ML-driven fraud evaluation rule."""

    @abstractmethod
    def evaluate(self, request: FraudCheckRequest) -> RuleEvaluationResult:
        """Evaluate the given transaction context and return risk score points and reasons."""
        pass
