import json
import logging
import os
import ssl
from typing import Any
from urllib import error, request

import certifi

logger = logging.getLogger(__name__)


class ApiGatewayClient:
    """Client for calling API Gateway to trigger Step Functions workflow."""

    def __init__(self, api_endpoint: str | None = None):
        self.api_endpoint = api_endpoint or os.environ.get("API_GATEWAY_ENDPOINT", "").strip()
        if not self.api_endpoint:
            raise ValueError("API_GATEWAY_ENDPOINT environment variable is required")

    def _ssl_context(self):
        """Create SSL context using certifi CA bundle."""
        return ssl.create_default_context(cafile=certifi.where())

    def trigger_onboarding(
        self,
        intake: dict[str, Any],
        slack_channel: str,
        slack_user: str,
    ) -> dict[str, Any]:
        """
        Trigger the onboarding workflow via API Gateway.

        Args:
            intake: Validated intake data
            slack_channel: Slack channel ID
            slack_user: Slack user ID

        Returns:
            Dict with executionArn, startDate, and message

        Raises:
            ApiGatewayError: If the API call fails
        """
        payload = {
            "intake": intake,
            "slack_channel": slack_channel,
            "slack_user": slack_user,
        }

        try:
            req = request.Request(
                url=self.api_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with request.urlopen(req, timeout=30, context=self._ssl_context()) as response:
                response_body = response.read().decode("utf-8")
                result = json.loads(response_body)

                logger.info(f"Successfully triggered onboarding workflow: {result.get('executionArn')}")
                return result

        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.error(f"API Gateway HTTP error {exc.code}: {detail}")
            raise ApiGatewayError(f"API call failed (HTTP {exc.code}): {detail}") from exc
        except error.URLError as exc:
            logger.error(f"API Gateway network error: {exc.reason}")
            raise ApiGatewayError(f"Network error: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse API response: {exc}")
            raise ApiGatewayError("Invalid JSON response from API") from exc
        except Exception as exc:
            logger.error(f"Unexpected error calling API Gateway: {exc}")
            raise ApiGatewayError(f"Unexpected error: {exc}") from exc

    def check_execution_status(self, execution_arn: str) -> dict[str, Any]:
        """
        Check the status of a Step Functions execution.

        Args:
            execution_arn: The execution ARN to check

        Returns:
            Dict with execution status details

        Raises:
            ApiGatewayError: If the API call fails
        """
        # Extract execution name from ARN for URL path
        # ARN format: arn:aws:states:region:account:execution:stateMachineName:executionName
        status_url = f"{self.api_endpoint.replace('/onboard', '/status')}/{execution_arn}"

        try:
            req = request.Request(
                url=status_url,
                headers={"Accept": "application/json"},
                method="GET",
            )

            with request.urlopen(req, timeout=10, context=self._ssl_context()) as response:
                response_body = response.read().decode("utf-8")
                result = json.loads(response_body)
                return result

        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.error(f"Status check HTTP error {exc.code}: {detail}")
            raise ApiGatewayError(f"Status check failed (HTTP {exc.code}): {detail}") from exc
        except error.URLError as exc:
            logger.error(f"Status check network error: {exc.reason}")
            raise ApiGatewayError(f"Network error: {exc.reason}") from exc
        except Exception as exc:
            logger.error(f"Unexpected error checking status: {exc}")
            raise ApiGatewayError(f"Unexpected error: {exc}") from exc


class ApiGatewayError(Exception):
    """Exception raised for API Gateway errors."""
    pass
