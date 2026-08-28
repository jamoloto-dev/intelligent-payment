"""Fraud Service business logic layer."""
from typing import List, Optional
from shared.events.redis_client import EventBus
from shared.logging.logger import get_logger
from shared.schemas.common import FraudDecision, FraudRiskLevel
from shared.schemas.events import FraudReviewRequiredEvent
from services.fraud_service.app.rules.base import BaseFraudRule
from services.fraud_service.app.rules.rules import (
    AccountAgeRule,
    FailedPaymentsRule,
    GeolocationMismatchRule,
    HighAmountRule,
    VelocityRule,
)
from services.fraud_service.app.schemas.fraud import FraudCheckRequest, FraudCheckResponse
from services.fraud_service.app.storage.storage import FraudStorage

logger = get_logger("fraud-service")


class FraudService:
    """Evaluates transactions against fraud risk rules and decides outcomes."""

    def __init__(
        self,
        rules: Optional[List[BaseFraudRule]] = None,
        storage: Optional[FraudStorage] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.rules = rules or [
            HighAmountRule(),
            VelocityRule(),
            AccountAgeRule(),
            FailedPaymentsRule(),
            GeolocationMismatchRule(),
        ]
        self.storage = storage or FraudStorage()
        self.event_bus = event_bus

    async def evaluate_transaction(self, request: FraudCheckRequest) -> FraudCheckResponse:
        total_risk_score = 0.0
        reasons: List[str] = []
        rules_triggered: List[str] = []

        # Run all rules
        for rule in self.rules:
            result = rule.evaluate(request)
            if result.triggered:
                total_risk_score += result.score_increment
                rules_triggered.append(result.rule_name)
                if result.reason:
                    reasons.append(result.reason)

        # Cap score between 0.0 and 100.0
        final_score = min(100.0, max(0.0, total_risk_score))

        # Determine risk level and decision
        if final_score >= 80.0:
            risk_level = FraudRiskLevel.CRITICAL
            decision = FraudDecision.REJECT
        elif final_score >= 50.0:
            risk_level = FraudRiskLevel.HIGH
            decision = FraudDecision.REVIEW
        elif final_score >= 25.0:
            risk_level = FraudRiskLevel.MEDIUM
            decision = FraudDecision.REVIEW
        else:
            risk_level = FraudRiskLevel.LOW
            decision = FraudDecision.APPROVE

        if not reasons:
            reasons.append("Standard low-risk profile")

        response = FraudCheckResponse(
            transaction_id=request.transaction_id,
            order_id=request.order_id,
            user_id=request.user_id,
            risk_score=final_score,
            risk_level=risk_level,
            decision=decision,
            reasons=reasons,
            rules_triggered=rules_triggered,
            metadata={"payment_method": request.payment_method},
        )

        # Persist evaluation
        await self.storage.save(response)

        # If flagged for REVIEW or REJECT, publish security event
        if decision in [FraudDecision.REVIEW, FraudDecision.REJECT] and self.event_bus:
            event = FraudReviewRequiredEvent(
                transaction_id=request.transaction_id,
                order_id=request.order_id,
                user_id=request.user_id,
                risk_score=final_score,
                risk_level=risk_level.value,
                decision=decision.value,
                reasons=reasons,
            )
            await self.event_bus.publish("fraud_events", event)

        logger.info(
            f"Fraud check evaluated for tx {request.transaction_id}: score={final_score}, decision={decision.value}",
            extra={"event": "fraud_evaluated", "status": decision.value, "extra_data": {"score": final_score}},
        )
        return response

    async def get_by_transaction_id(self, transaction_id: str) -> Optional[FraudCheckResponse]:
        return await self.storage.get_by_transaction_id(transaction_id)

    async def list_evaluations(self, limit: int = 50) -> List[FraudCheckResponse]:
        return await self.storage.list_evaluations(limit=limit)
