"""Standardized Error Responses for Intelligent Payment Platform."""
from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error object returned across all APIs."""
    error: str = Field(..., description="Machine-readable error code (e.g. USER_NOT_FOUND)")
    message: str = Field(..., description="Human-readable error explanation")
    request_id: Optional[str] = Field(None, description="Unique trace/correlation ID for the request")
    details: Optional[Any] = Field(None, description="Optional validation or context details")


class HTTPErrorResponse(BaseModel):
    """Envelope for standard error responses."""
    error: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Any] = None
