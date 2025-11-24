"""SES based notification helper."""

from __future__ import annotations

import os
from typing import Iterable, Optional

import boto3
from botocore.exceptions import ClientError


class SesNotifier:
    def __init__(
        self,
        sender: Optional[str] = None,
        ses_client=None,
    ) -> None:
        self.sender = sender or os.environ.get("SES_SENDER_EMAIL")
        self._ses = ses_client or boto3.client("ses") if self.sender else None

    def send(self, subject: str, body: str, recipients: Iterable[str]) -> None:
        if not self.sender or not self._ses:
            return
        targets = [addr for addr in recipients if addr]
        if not targets:
            return
        try:
            self._ses.send_email(
                Source=self.sender,
                Destination={"ToAddresses": targets},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                },
            )
        except ClientError as error:
            # Notification failures should not crash the Lambda invocation.
            print(f"SES send failed: {error}")
