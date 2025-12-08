import json
import boto3
import time
from urllib.parse import unquote_plus

s3 = boto3.client("s3")
textract = boto3.client("textract")


def lambda_handler(event, context):
    """
    Triggered by S3 ObjectCreated events on keys like:
      <user_id>/images/<filename>

    For each new image:
      - Download from S3
      - Run Textract OCR
      - Save result as JSON to:
          <user_id>/text/<filename>.json
    """

    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        # Expect: user_id/images/filename.ext
        parts = key.split("/")
        if len(parts) < 3:
            print(f"Skipping invalid key: {key}")
            continue

        user_id = parts[0]
        filename = parts[-1]

        print(f"Processing bucket={bucket}, key={key}, user_id={user_id}, filename={filename}")

        # 1) Get image bytes from S3
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            image_bytes = obj["Body"].read()
        except Exception as e:
            print(f"Error getting S3 object {key}: {e}")
            continue

        # 2) Call Textract
        try:
            response = textract.detect_document_text(
                Document={"Bytes": image_bytes}
            )
        except Exception as e:
            print(f"Textract error for {key}: {e}")
            continue

        # 3) Extract lines of text
        lines = [
            block["Text"]
            for block in response.get("Blocks", [])
            if block.get("BlockType") == "LINE"
        ]
        extracted_text = "\n".join(lines)
        print(f"OCR text for {filename}:\n{extracted_text}")

        # 4) Build JSON payload for this image
        ocr_entry = {
            "user_id": user_id,
            "image_name": filename,
            "s3_key": key,
            "text": extracted_text,
            "timestamp": int(time.time()),
        }

        # 5) Store as per-image JSON: <user_id>/text/<filename>.json
        json_key = f"{user_id}/text/{filename}.json"

        try:
            s3.put_object(
                Bucket=bucket,
                Key=json_key,
                Body=json.dumps(ocr_entry),
                ContentType="application/json",
            )
            print(f"Stored OCR JSON at {json_key}")
        except Exception as e:
            print(f"Error writing OCR JSON {json_key}: {e}")
            continue

    return {"statusCode": 200, "body": "Textract OCR processing completed"}
