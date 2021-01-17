def unwrapPoint(pt):
    return pt.x, pt.y

def converBoundsToRect(bounds):
    if bounds is None:
        return (0, 0, 0, 0)
    xMin, yMin, xMax, yMax = bounds
    x = xMin
    y = yMin
    w = xMax - xMin
    h = yMax - yMin
    return (x, y, w, h)