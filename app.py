import os
import uuid
import boto3
from flask import Flask, render_template, request, redirect, url_for, flash

# Load config from environment
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

# For now, hardcode a demo user_id
DEMO_USER_ID = "user-1234"  # later replace with real user_id from login

s3 = boto3.client("s3", region_name=AWS_REGION)

app = Flask(__name__)
app.secret_key = SECRET_KEY


def list_user_images(user_id: str):
    """List all image keys for the user under <user_id>/images/."""
    prefix = f"{user_id}/images/"
    objects = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
    keys = []
    for item in objects.get("Contents", []):
        key = item["Key"]
        if key.endswith("/"):
            continue
        keys.append(key)
    return keys


def load_ocr_results(user_id: str):
    """Load OCR JSON for each image from <user_id>/text/*.json."""
    prefix = f"{user_id}/text/"
    resp = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)

    results = []
    for item in resp.get("Contents", []):
        key = item["Key"]
        if not key.endswith(".json"):
            continue
        obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        data = obj["Body"].read().decode("utf-8")

        try:
            entry = json.loads(data)
        except Exception:
            continue
        results.append(entry)

    # Sort by timestamp (newest first)
    results.sort(key=lambda r: r.get("timestamp", 0), reverse=True)
    return results


@app.route("/", methods=["GET"])
def index():
    user_id = DEMO_USER_ID  # later replace with session["user_id"] and need to lool into this

    image_keys = list_user_images(user_id)
    ocr_entries = load_ocr_results(user_id)

    # Map image_name -> OCR text for easy display
    ocr_by_image = {e["image_name"]: e["text"] for e in ocr_entries}

    # Build a simple list of dicts for template
    images = []
    for key in image_keys:
        filename = key.split("/")[-1]
        ocr_text = ocr_by_image.get(filename, "(no OCR yet)")
        # Public URL (if bucket is public) or you can use presigned URLs
        image_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
        images.append(
            {
                "filename": filename,
                "key": key,
                "url": image_url,
                "ocr_text": ocr_text,
            }
        )

    return render_template("index.html", images=images, user_id=user_id)


@app.route("/upload", methods=["POST"])
def upload():
    user_id = DEMO_USER_ID  # later use real user id

    file = request.files.get("file")
    if not file or file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("index"))

    # Simple extension check
    allowed_ext = (".jpg", ".jpeg", ".png", ".pdf")
    filename = file.filename
    if not any(filename.lower().endswith(ext) for ext in allowed_ext):
        flash("Unsupported file type. Use JPG/PNG/PDF.", "error")
        return redirect(url_for("index"))

    # Make filename unique
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    key = f"{user_id}/images/{unique_name}"

    try:
        s3.upload_fileobj(file, S3_BUCKET_NAME, key)
        flash("File uploaded successfully. OCR will run shortly.", "success")
    except Exception as e:
        print(f"Upload error: {e}")
        flash("Error uploading file.", "error")

    return redirect(url_for("index"))


if __name__ == "__main__":
    # For dev only; in prod use gunicorn + nginx
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
