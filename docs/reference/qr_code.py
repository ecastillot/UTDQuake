from pathlib import Path
import qrcode

url = "https://ecastillot.github.io/utdquake/references/index.html"
path = Path(__file__).parent / "utdquake_references_QR.png"
qr = qrcode.make(url)
qr.save(path)
print("QR code saved to",path)