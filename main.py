# main.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from io import BytesIO
import random
import string
import segno
import barcode
from barcode.writer import ImageWriter, SVGWriter

app = FastAPI(title="QR & Barcode Generator")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------- Models ----------
class QRRequest(BaseModel):
    link: str
    output_format: str = "png"


class BarcodeRequest(BaseModel):
    text: str = ""
    auto: bool = False
    barcode_format: str = "code128"
    output_format: str = "png"


# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/qrcode")
async def generate_qr(req: QRRequest):
    link = req.link.strip()
    if not link:
        raise HTTPException(400, "Link zaroori hai.")

    fmt = req.output_format.lower()
    if fmt not in ("png", "svg"):
        raise HTTPException(400, "Format sirf png ya svg ho sakta hai.")

    try:
        qr = segno.make(link, error="m")
        buf = BytesIO()
        if fmt == "svg":
            qr.save(buf, kind="svg", scale=10, dark="#000000", light="#ffffff")
            media_type = "image/svg+xml"
        else:
            qr.save(buf, kind="png", scale=10, dark="#000000", light="#ffffff")
            media_type = "image/png"
        buf.seek(0)
        return Response(content=buf.read(), media_type=media_type)
    except Exception as e:
        raise HTTPException(500, f"QR generation failed: {e}")


@app.post("/api/barcode")
async def generate_barcode(req: BarcodeRequest):
    fmt = req.barcode_format.lower()
    valid_formats = {"code128", "code39", "ean13", "ean8", "upca", "isbn13", "itf"}
    if fmt not in valid_formats:
        raise HTTPException(400, f"Format '{fmt}' supported nahi hai.")

    out_fmt = req.output_format.lower()
    if out_fmt not in ("png", "svg"):
        raise HTTPException(400, "Format sirf png ya svg ho sakta hai.")

    text = req.text.strip()

    # Auto-generate valid value
    if req.auto or not text:
        text = _auto_value(fmt)

    # Validate length for numeric-only formats
    try:
        _validate(fmt, text)
    except ValueError as e:
        raise HTTPException(400, str(e))

    try:
        barcode_class = barcode.get_barcode_class(fmt)
        buf = BytesIO()
        if out_fmt == "svg":
            writer = SVGWriter()
            media_type = "image/svg+xml"
        else:
            writer = ImageWriter()
            media_type = "image/png"

        bc = barcode_class(text, writer=writer)
        # For PNG, tune writer options for clean packaging-ready output
        if out_fmt == "png":
            bc.write(buf, options={
                "module_width": 0.3,
                "module_height": 15.0,
                "quiet_zone": 6.5,
                "font_size": 10,
                "text_distance": 5.0,
                "background": "white",
                "foreground": "black",
            })
        else:
            bc.write(buf)

        buf.seek(0)
        return Response(content=buf.read(), media_type=media_type)
    except Exception as e:
        raise HTTPException(500, f"Barcode generation failed: {e}")


# ---------- Helpers ----------
def _auto_value(fmt: str) -> str:
    """Format ke hisaab se valid random value banata hai."""
    digits = string.digits
    alnum = string.ascii_uppercase + string.digits

    if fmt in ("ean13", "isbn13"):
        return "".join(random.choices(digits, k=12))   # checksum auto
    if fmt == "ean8":
        return "".join(random.choices(digits, k=7))
    if fmt == "upca":
        return "".join(random.choices(digits, k=11))
    if fmt == "itf":
        return "".join(random.choices(digits, k=12))   # even length
    if fmt == "code39":
        return "".join(random.choices(alnum, k=10))
    # code128 (default)
    return "".join(random.choices(alnum, k=12))


def _validate(fmt: str, text: str):
    """Length / character validation for stricter formats."""
    if fmt in ("ean13", "isbn13"):
        if not (text.isdigit() and len(text) in (12, 13)):
            raise ValueError("EAN-13 / ISBN-13 ke liye 12 ya 13 digits chahiye.")
    elif fmt == "ean8":
        if not (text.isdigit() and len(text) in (7, 8)):
            raise ValueError("EAN-8 ke liye 7 ya 8 digits chahiye.")
    elif fmt == "upca":
        if not (text.isdigit() and len(text) in (11, 12)):
            raise ValueError("UPC-A ke liye 11 ya 12 digits chahiye.")
    elif fmt == "itf":
        if not (text.isdigit() and len(text) % 2 == 0):
            raise ValueError("ITF ke liye even number of digits chahiye.")
    elif fmt == "code39":
        allowed = set(string.ascii_uppercase + string.digits + " -.$/+%")
        if not set(text.upper()).issubset(allowed):
            raise ValueError("Code39 mein sirf A-Z, 0-9 aur - . $ / + % allowed hain.")