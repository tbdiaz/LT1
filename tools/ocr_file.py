import Vision, sys
from Foundation import NSURL
img = NSURL.fileURLWithPath_(sys.argv[1])
handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(img, None)
req = Vision.VNRecognizeTextRequest.alloc().init()
req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
req.setUsesLanguageCorrection_(True)
req.setRecognitionLanguages_(["es-ES", "en-US"])
handler.performRequests_error_([req], None)
res = req.results()
out = []
for o in res:
    s = o.topCandidates_(1)[0].string()
    b = o.boundingBox()
    cx = b.origin.x + b.size.width/2
    cy = b.origin.y + b.size.height/2
    out.append((cx, cy, s))
out.sort(key=lambda t: (-round(t[1],3), t[0]))
print("== OCR:", sys.argv[1], "==")
for x,y,s in out:
    print(f"  ({x:.2f},{y:.2f}) {s}")
