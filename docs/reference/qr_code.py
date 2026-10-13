from pathlib import Path
import qrcode

url = "https://github.com/ecastillot/UTDQuake/blob/main/docs/reference/references.md"
path = Path(__file__).parent / "utdquake_references_QR.png"
qr = qrcode.make(url)
qr.save(path)
print("QR code saved to",path)