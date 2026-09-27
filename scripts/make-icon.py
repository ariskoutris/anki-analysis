"""
Renders assets/icon.png (1024px macOS app icon) with AppKit (pyobjc, installed with pywebview).

Run with:  uv run python scripts/make-icon.py assets/icon.png
"""
import sys
from AppKit import (NSBitmapImageRep, NSGraphicsContext, NSColor, NSBezierPath,
    NSGradient, NSAffineTransform, NSShadow, NSMakeRect, NSMakePoint, NSPNGFileType,
    NSCalibratedRGBColorSpace, NSMakeSize)

def hex_(h, a=1.0):
    h = h.lstrip('#'); r, g, b = (int(h[i:i+2], 16)/255 for i in (0, 2, 4))
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)

S = 1024
rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
    None, S, S, 8, 4, True, False, NSCalibratedRGBColorSpace, 0, 0)
ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.setCurrentContext_(ctx)

# macOS icon grid: 824px body, ~185px corner radius
body = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(NSMakeRect(100, 100, 824, 824), 185, 185)
sh = NSShadow.alloc().init(); sh.setShadowOffset_(NSMakeSize(0, -12)); sh.setShadowBlurRadius_(28)
sh.setShadowColor_(NSColor.colorWithCalibratedWhite_alpha_(0, 0.45))
NSGraphicsContext.saveGraphicsState(); sh.set(); hex_('#111217').setFill(); body.fill(); NSGraphicsContext.restoreGraphicsState()
NSGradient.alloc().initWithStartingColor_endingColor_(hex_('#1d2130'), hex_('#0b0c0e')).drawInBezierPath_angle_(body, -90)
hex_('#2a2d3a').setStroke(); body.setLineWidth_(4); body.stroke()

DY = 30  # lift the card stack so its bounding box sits at the optical center

def card(x, y, w, h, angle, color):
    t = NSAffineTransform.transform(); t.translateXBy_yBy_(x + w/2, y + h/2 + DY); t.rotateByDegrees_(angle)
    p = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(NSMakeRect(-w/2, -h/2, w, h), 44, 44)
    p.transformUsingAffineTransform_(t)
    NSGraphicsContext.saveGraphicsState()
    s = NSShadow.alloc().init(); s.setShadowOffset_(NSMakeSize(0, -8)); s.setShadowBlurRadius_(24)
    s.setShadowColor_(NSColor.colorWithCalibratedWhite_alpha_(0, 0.5)); s.set()
    color.setFill(); p.fill(); NSGraphicsContext.restoreGraphicsState()

# back card (tilted, accent) + front card
card(262, 300, 500, 380, 9, hex_('#b07aff'))
card(262, 262, 500, 380, 0, hex_('#f3f4f8'))

# rising retention curve on the front card
pts = [(x, y + DY) for x, y in [(334, 350), (420, 406), (486, 390), (570, 474), (676, 544)]]
line = NSBezierPath.bezierPath(); line.moveToPoint_(NSMakePoint(*pts[0]))
for p in pts[1:]: line.lineToPoint_(NSMakePoint(*p))
line.setLineWidth_(34); line.setLineCapStyle_(1); line.setLineJoinStyle_(1)
hex_('#5b8dff').setStroke(); line.stroke()
x, y = pts[-1]
dot = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(x-36, y-36, 72, 72))
hex_('#2dd4a8').setFill(); dot.fill()
hex_('#f3f4f8').setStroke(); dot.setLineWidth_(10); dot.stroke()

NSGraphicsContext.restoreGraphicsState()
rep.representationUsingType_properties_(NSPNGFileType, {}).writeToFile_atomically_(sys.argv[1], True)
