"""Deterministic Fraud Evaluation Rules."""
from datetime import datetime, timezone
from services.fraud_service.app.config.settings import settings
from services.fraud_service.app.rules.base import BaseFraudRule, RuleEvaluationResult
from services.fraud_service.app.schemas.fraud import FraudCheckRequest


class HighAmountRule(BaseFraudRule):
    """Flags unusually large transaction amounts."""

    def __init__(
        self,
        high_threshold: float = settings.HIGH_AMOUNT_THRESHOLD,
        critical_threshold: float = settings.CRITICAL_AMOUNT_THRESHOLD,
    ):
        self.high_threshold = high_threshold
        self.critical_threshold = critical_threshold

    def evaluate(self, request: FraudCheckRequest) -> RuleEvaluationResult:
        amt = float(request.amount)
        if amt >= self.critical_threshold:
            return RuleEvaluationResult(
                rule_name="CriticalAmountRule",
                score_increment=45.0,
                reason=f"Transaction amount ({amt} {request.currency}) exceeds critical threshold ({self.critical_threshold})",
                triggered=True,
            )
        elif amt >= self.high_threshold:
            return RuleEvaluationResult(
                rule_name="HighAmountRule",
                score_increment=25.0,
                reason=f"Transaction amount ({amt} {request.currency}) exceeds standard threshold ({self.high_threshold})",
                triggered=True,
            )
        return RuleEvaluationResult(rule_name="HighAmountRule", score_increment=0.0, triggered=False)


class VelocityRule(BaseFraudRule):
    """Flags high frequency of transactions in a short time window."""

    def __init__(self, max_hourly_velocity: int = settings.MAX_VELOCITY_TX_PER_HOUR):
        self.max_hourly_velocity = max_hourly_velocity

    def evaluate(self, request: FraudCheckRequest) -> RuleEvaluationResult:
        count = request.recent_transactions_count_1h or 0
        if count >= self.max_hourly_velocity:
            return RuleEvaluationResult(
                rule_name="HighVelocityRule",
                score_increment=35.0,
                reason=f"High transaction velocity: {count} attempts in the past hour (limit: {self.max_hourly_velocity})",
                triggered=True,
            )
        elif count >= 3:
            return RuleEvaluationResult(
                rule_name="ModerateVelocityRule",
                score_increment=15.0,
                reason=f"Elevated transaction frequency: {count} attempts recently",
                triggered=True,
            )
        return RuleEvaluationResult(rule_name="VelocityRule", score_increment=0.0, triggered=False)


class AccountAgeRule(BaseFraudRule):
    """Flags new accounts with rapid high-value transactions."""

    def evaluate(self, request: FraudCheckRequest) -> RuleEvaluationResult:
        if not request.account_created_at:
            return RuleEvaluationResult(rule_name="AccountAgeRule", score_increment=0.0, triggered=False)

        now = datetime.now(timezone.utc)
        acct_date = request.account_created_at
        if acct_date.tzinfo is None:
            acct_date = acct_date.replace(tzinfo=timezone.utc)

        age_hours = (now - acct_date).total_seconds() / 3600.0
        if age_hours < 24.0:
            return RuleEvaluationResult(
                rule_name="NewAccountRule",
                score_increment=20.0,
                reason=f"New account created only {round(age_hours, 1)} hours ago",
                triggered=True,
            )
        return RuleEvaluationResult(rule_name="AccountAgeRule", score_increment=0.0, triggered=False)


class FailedPaymentsRule(BaseFraudRule):
    """Flags repeated previous failed payment attempts."""

    def __init__(self, max_failed: int = settings.MAX_FAILED_ATTEMPTS):
        self.max_failed = max_failed

    def evaluate(self, request: FraudCheckRequest) -> RuleEvaluationResult:
        failed_count = request.recent_failed_payments_24h or 0
        if failed_count >= self.max_failed:
            return RuleEvaluationResult(
                rule_name="RepeatedFailuresRule",
                score_increment=40.0,
                reason=f"Multiple recent failed payments detected: {failed_count} failures in last 24h",
                triggered=True,
            )
        elif failed_count > 0:
            return RuleEvaluationResult(
                rule_name="RecentFailureRule",
                score_increment=10.0 * failed_count,
                reason=f"Previous failed payment attempt detected ({failed_count} attempt(s))",
                triggered=True,
            )
        return RuleEvaluationResult(rule_name="FailedPaymentsRule", score_increment=0.0, triggered=False)


class GeolocationMismatchRule(BaseFraudRule):
    """Flags country mismatches between IP location and billing address."""

    def evaluate(self, request: FraudCheckRequest) -> RuleEvaluationResult:
        if request.billing_country and request.ip_country:
            if request.billing_country.upper() != request.ip_country.upper():
                return RuleEvaluationResult(
                    rule_name="GeolocationMismatchRule",
                    score_increment=25.0,
                    reason=f"Geolocation mismatch: Billing country '{request.billing_country}' != IP country '{request.ip_country}'",
                    triggered=True,
                )
        return RuleEvaluationResult(rule_name="GeolocationMismatchRule", score_increment=0.0, triggered=False)
