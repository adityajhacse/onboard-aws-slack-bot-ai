"""
Helper module for DynamoDB operations.
Provides functions to track execution status and store service records.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DynamoDBHelper:
    """Helper class for DynamoDB operations."""

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ.get('DYNAMODB_TABLE', 'det-onboarding-prod-executions')
        self.logs_table_name = os.environ.get('DYNAMODB_LOGS_TABLE', 'det-onboarding-prod-execution-logs')
        self.table = self.dynamodb.Table(self.table_name)
        self.logs_table = self.dynamodb.Table(self.logs_table_name)

    def create_execution_record(
        self,
        execution_id: str,
        intake: dict[str, Any],
        slack_channel: str,
        slack_user: str,
    ) -> dict[str, Any]:
        """
        Create initial execution record with intake data.

        Args:
            execution_id: Unique execution identifier
            intake: Complete intake data from form
            slack_channel: Slack channel ID
            slack_user: Slack user ID

        Returns:
            Created record
        """
        now = datetime.utcnow()
        ttl = int((now + timedelta(days=90)).timestamp())

        record = {
            'execution_id': execution_id,
            'status': 'RUNNING',
            'current_step': 'ValidateIntake',
            'project_name': intake.get('project_name', 'Unknown'),
            'project_slug': intake.get('project_slug', ''),
            'slack_channel': slack_channel,
            'slack_user': slack_user,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'ttl': ttl,
            'intake_data': self._convert_to_dynamodb(intake),
            'steps': {
                'ValidateIntake': {'status': 'PENDING'},
                'CreateGitHubBranch': {'status': 'PENDING'},
                'CommitToGitHub': {'status': 'PENDING'},
                'CreateHCPProject': {'status': 'PENDING'},
                'CreateWorkspaces': {'status': 'PENDING'},
                'ConfigureVariables': {'status': 'PENDING'},
            },
            'results': {},
            'errors': [],
        }

        try:
            self.table.put_item(Item=record)
            logger.info(f"Created execution record: {execution_id}")
            return record
        except ClientError as e:
            logger.error(f"Failed to create execution record: {e}")
            raise

    def update_step_status(
        self,
        execution_id: str,
        step_name: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """
        Update status of a specific step.

        Args:
            execution_id: Execution identifier
            step_name: Name of the step
            status: Status (RUNNING, SUCCEEDED, FAILED, SKIPPED)
            result: Optional result data from step
            error: Optional error message if failed
        """
        now = datetime.utcnow()
        update_expression = [
            'current_step = :step',
            'updated_at = :updated',
            f'steps.{step_name}.#status = :step_status',
        ]
        expression_values = {
            ':step': step_name,
            ':updated': now.isoformat(),
            ':step_status': status,
        }
        expression_names = {'#status': 'status'}

        if result:
            update_expression.append(f'steps.{step_name}.result = :result')
            expression_values[':result'] = self._convert_to_dynamodb(result)

        if error:
            update_expression.append(f'steps.{step_name}.error = :error')
            expression_values[':error'] = error

        if status == 'RUNNING':
            update_expression.append(f'steps.{step_name}.started_at = :started')
            expression_values[':started'] = now.isoformat()
        elif status in ('SUCCEEDED', 'FAILED'):
            update_expression.append(f'steps.{step_name}.completed_at = :completed')
            expression_values[':completed'] = now.isoformat()

        try:
            self.table.update_item(
                Key={'execution_id': execution_id},
                UpdateExpression='SET ' + ', '.join(update_expression),
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
            )
            logger.info(f"Updated step {step_name} status to {status} for {execution_id}")

            # Log to execution logs table
            self._log_step(execution_id, step_name, status, result, error)

        except ClientError as e:
            logger.error(f"Failed to update step status: {e}")
            raise

    def update_execution_status(
        self,
        execution_id: str,
        status: str,
        final_result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        """
        Update overall execution status.

        Args:
            execution_id: Execution identifier
            status: Overall status (RUNNING, SUCCEEDED, FAILED)
            final_result: Optional final result data
            error_message: Optional error message if failed
        """
        now = datetime.utcnow()
        update_expression = ['#status = :status', 'updated_at = :updated']
        expression_values = {
            ':status': status,
            ':updated': now.isoformat(),
        }
        expression_names = {'#status': 'status'}

        if final_result:
            update_expression.append('#result = :result')
            expression_values[':result'] = self._convert_to_dynamodb(final_result)
            expression_names['#result'] = 'result'

        if error_message:
            update_expression.append('error_message = :error')
            expression_values[':error'] = error_message

        if status in ('SUCCEEDED', 'FAILED'):
            update_expression.append('completed_at = :completed')
            expression_values[':completed'] = now.isoformat()

        try:
            self.table.update_item(
                Key={'execution_id': execution_id},
                UpdateExpression='SET ' + ', '.join(update_expression),
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
            )
            logger.info(f"Updated execution status to {status} for {execution_id}")
        except ClientError as e:
            logger.error(f"Failed to update execution status: {e}")
            raise

    def add_workspace_result(
        self,
        execution_id: str,
        environment: str,
        workspace_id: str,
        workspace_name: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        """
        Add workspace creation result.

        Args:
            execution_id: Execution identifier
            environment: Environment name (Dev, QA, Prod)
            workspace_id: Created workspace ID
            workspace_name: Created workspace name
            success: Whether creation succeeded
            error: Optional error message
        """
        workspace_data = {
            'workspace_id': workspace_id,
            'workspace_name': workspace_name,
            'success': success,
            'created_at': datetime.utcnow().isoformat(),
        }
        if error:
            workspace_data['error'] = error

        try:
            self.table.update_item(
                Key={'execution_id': execution_id},
                UpdateExpression=f'SET results.workspaces.{environment} = :workspace',
                ExpressionAttributeValues={
                    ':workspace': self._convert_to_dynamodb(workspace_data)
                },
            )
            logger.info(f"Added workspace result for {environment}: {workspace_name}")
        except ClientError as e:
            logger.error(f"Failed to add workspace result: {e}")
            raise

    def get_execution(self, execution_id: str) -> dict[str, Any] | None:
        """
        Get execution record by ID.

        Args:
            execution_id: Execution identifier

        Returns:
            Execution record or None if not found
        """
        try:
            response = self.table.get_item(Key={'execution_id': execution_id})
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Failed to get execution: {e}")
            return None

    def get_executions_by_channel(
        self,
        slack_channel: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get recent executions for a Slack channel.

        Args:
            slack_channel: Slack channel ID
            limit: Maximum number of records to return

        Returns:
            List of execution records
        """
        try:
            response = self.table.query(
                IndexName='slack-channel-index',
                KeyConditionExpression='slack_channel = :channel',
                ExpressionAttributeValues={':channel': slack_channel},
                ScanIndexForward=False,  # Sort by created_at descending
                Limit=limit,
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Failed to query executions: {e}")
            return []

    def get_executions_by_status(
        self,
        status: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get executions by status.

        Args:
            status: Status to filter by (RUNNING, SUCCEEDED, FAILED)
            limit: Maximum number of records to return

        Returns:
            List of execution records
        """
        try:
            response = self.table.query(
                IndexName='status-index',
                KeyConditionExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': status},
                ScanIndexForward=False,
                Limit=limit,
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Failed to query by status: {e}")
            return []

    def get_execution_logs(
        self,
        execution_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get detailed logs for an execution.

        Args:
            execution_id: Execution identifier
            limit: Maximum number of log entries

        Returns:
            List of log entries
        """
        try:
            response = self.logs_table.query(
                KeyConditionExpression='execution_id = :exec_id',
                ExpressionAttributeValues={':exec_id': execution_id},
                ScanIndexForward=True,  # Sort by timestamp ascending
                Limit=limit,
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"Failed to get execution logs: {e}")
            return []

    def _log_step(
        self,
        execution_id: str,
        step_name: str,
        status: str,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> None:
        """
        Log step execution to execution logs table.

        Args:
            execution_id: Execution identifier
            step_name: Name of the step
            status: Step status
            result: Optional result data
            error: Optional error message
        """
        now = datetime.utcnow()
        ttl = int((now + timedelta(days=90)).timestamp())

        log_entry = {
            'execution_id': execution_id,
            'timestamp': int(now.timestamp() * 1000),  # Milliseconds
            'step_name': step_name,
            'status': status,
            'log_time': now.isoformat(),
            'ttl': ttl,
        }

        if result:
            log_entry['result'] = self._convert_to_dynamodb(result)
        if error:
            log_entry['error'] = error

        try:
            self.logs_table.put_item(Item=log_entry)
        except ClientError as e:
            logger.warning(f"Failed to write execution log: {e}")

    def _convert_to_dynamodb(self, obj: Any) -> Any:
        """
        Convert Python objects to DynamoDB-compatible format.
        Handles floats by converting to Decimal.

        Args:
            obj: Python object to convert

        Returns:
            DynamoDB-compatible object
        """
        if isinstance(obj, dict):
            return {k: self._convert_to_dynamodb(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_dynamodb(item) for item in obj]
        elif isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, (int, str, bool, type(None))):
            return obj
        else:
            return str(obj)


# Global instance
_helper = None


def get_helper() -> DynamoDBHelper:
    """Get or create global DynamoDB helper instance."""
    global _helper
    if _helper is None:
        _helper = DynamoDBHelper()
    return _helper
