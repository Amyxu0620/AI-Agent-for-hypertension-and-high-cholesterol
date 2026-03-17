import boto3
from app.config import AWS_REGION, SES_SOURCE_EMAIL

ses = boto3.client("ses", region_name=AWS_REGION)


def send_email(to_addresses, subject, html_body, text_body=""):
    if isinstance(to_addresses, str):
        to_addresses = [to_addresses]

    return ses.send_email(
        Source=SES_SOURCE_EMAIL,
        Destination={"ToAddresses": to_addresses},
        Message={
            "Subject": {"Data": subject},
            "Body": {
                "Html": {"Data": html_body},
                "Text": {"Data": text_body or "Please use an HTML-compatible email client."}
            }
        }
    )
