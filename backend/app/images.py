import io
import warnings
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError

from .db import Product, ProductImage
from .security import Actor, DB
from .workspace import audit, owned, product_view

router = APIRouter(tags=["product images"])
MAX_BYTES = 5 * 1024 * 1024


@router.post("/products/{key}/image")
async def upload_image(key: UUID, request: Request, db: DB, user: Actor):
    product = owned(db, Product, key, user)
    if request.headers.get("content-type", "").split(";")[0] not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(415, "Upload a PNG, JPEG or WebP image")
    length = request.headers.get("content-length")
    if length and length.isdecimal() and int(length) > MAX_BYTES:
        raise HTTPException(413, "Image must be at most 5 MB")
    data = bytearray()
    async for block in request.stream():
        data.extend(block)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Image must be at most 5 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {"PNG", "JPEG", "WEBP"} or image.width * image.height > 16_000_000:
                    raise ValueError("Invalid image format or dimensions")
                image.load()
                image.thumbnail((1600, 1600))
                clean = image.convert("RGBA")
                clean.info.clear()
                output = io.BytesIO()
                clean.save(output, format="PNG", optimize=True)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise HTTPException(422, "Image could not be decoded. Use a valid image under 16 megapixels.") from None
    stored = db.get(ProductImage, product.id)
    if stored:
        stored.content = output.getvalue()
    else:
        db.add(ProductImage(product_id=product.id, content=output.getvalue()))
    product.attributes = {**product.attributes, "packaging_image": f"/api/v1/products/{product.id}/image"}
    audit(db, user, "product.image.upload", product.id)
    db.commit()
    return product_view(product)


@router.get("/products/{key}/image")
def image(key: UUID, db: DB, user: Actor):
    product = owned(db, Product, key, user)
    stored = db.get(ProductImage, product.id)
    if stored is None:
        raise HTTPException(404, "Packaging image not found")
    return Response(stored.content, media_type="image/png")


@router.delete("/products/{key}/image", status_code=204)
def remove_image(key: UUID, db: DB, user: Actor):
    product = owned(db, Product, key, user)
    stored = db.get(ProductImage, product.id)
    if stored:
        db.delete(stored)
    product.attributes = {**product.attributes, "packaging_image": None}
    audit(db, user, "product.image.delete", product.id)
    db.commit()
