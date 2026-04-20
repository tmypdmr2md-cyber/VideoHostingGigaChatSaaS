import os
from dataclasses import dataclass
from typing import Optional

from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

IMAGEKIT_PRIVATE_KEY = os.getenv("IMAGEKIT_PRIVATE_KEY", "")
IMAGEKIT_PUBLIC_KEY = os.getenv("IMAGEKIT_PUBLIC_KEY", "")
IMAGEKIT_URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT", "")
IMAGEKIT_FOLDER = os.getenv("IMAGEKIT_FOLDER", "/videoFastAPI")


@dataclass
class UploadedAsset:
    file_id: str
    url: str
    file_path: str
    size_bytes: int


def _client() -> ImageKit:
    if not (IMAGEKIT_PRIVATE_KEY and IMAGEKIT_PUBLIC_KEY and IMAGEKIT_URL_ENDPOINT):
        raise RuntimeError(
            "ImageKit credentials are missing: set IMAGEKIT_PRIVATE_KEY, "
            "IMAGEKIT_PUBLIC_KEY, IMAGEKIT_URL_ENDPOINT in .env"
        )
    return ImageKit(
        private_key=IMAGEKIT_PRIVATE_KEY,
        public_key=IMAGEKIT_PUBLIC_KEY,
        url_endpoint=IMAGEKIT_URL_ENDPOINT,
    )


def upload_bytes(
    data: bytes,
    file_name: str,
    is_private: bool = True,
    tags: Optional[list[str]] = None,
) -> UploadedAsset:
    """Uploads raw bytes to ImageKit. Private assets require signed URLs to be viewed."""
    client = _client()
    options = UploadFileRequestOptions(
        folder=IMAGEKIT_FOLDER,
        is_private_file=is_private,
        use_unique_file_name=True,
        tags=tags or [],
    )
    response = client.upload_file(file=data, file_name=file_name, options=options)

    if getattr(response, "response_metadata", None) and response.response_metadata.http_status_code >= 400:
        raise RuntimeError(f"ImageKit upload failed: {response.response_metadata.raw}")

    return UploadedAsset(
        file_id=response.file_id,
        url=response.url,
        file_path=response.file_path,
        size_bytes=int(response.size or len(data)),
    )


def generate_signed_url(file_path: str, expire_seconds: int = 300) -> str:
    """Returns a time-limited signed URL for a (typically private) ImageKit asset."""
    client = _client()
    return client.url(
        {
            "path": file_path,
            "signed": True,
            "expire_seconds": expire_seconds,
        }
    )


def delete_asset(file_id: str) -> None:
    client = _client()
    client.delete_file(file_id=file_id)
