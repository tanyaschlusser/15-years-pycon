from collections import OrderedDict

GOLDEN_RATIO = 1.4  # cheat; 1.618
COLORS = OrderedDict([
  ('Implementation/multi-language', (190,186,218)),
  ('Python language', (255,255,179)),
  ('Data', (253,180,98)),
  ('Web/Applications', (179,222,105)),
  ('Software development', (128,177,211)),
  ('Infrastructure', (252,205,229)),
  ('Science', (217,217,217)),
  ('Community', (141,211,199)),
  ('Other', (188,128,189)),
  ('Best practices', (251,128,114))
])

class BaseImage(object):
    def __init__(self, fname, aspect_ratio=1.):
        self.fname = fname
        self.ratio = aspect_ratio  # width / height
        self.img = None


class Image(BaseImage):    
    def load(self):
        self.img = loadImage(self.fname)
    
    def put(self, x, y, width=None, height=None):
        if self.img is None:
            self.load()
        if width == height == None:
            image(self.img, x, y)
        else:
            if width == None:
                h = height
                w = h * self.ratio
            elif height == None:
                w = width
                h = w / self.ratio
            else:
                w = width
                h = height
            image(self.img, x, y, w, h)

        
class Shape(BaseImage):
    def load(self):
        self.img = loadShape(self.fname)
        
    def put(self, x, y, width=None, height=None):
        if self.img is None:
            self.load()
        if width == height == None:
            shape(self.img, x, y)
        else:
            if width == None:
                h = height
                w = h * self.ratio
            elif height == None:
                w = width
                h = w / self.ratio
            else:
                w = width
                h = height
            shape(self.img, x, y, w, h)


django = Image("django.png")
heart = Image("heart.png", aspect_ratio=149./145)
plone = Image("plone.png")
pycon = Image("python.png")
pydata = Image("pydata.png", aspect_ratio=23./48)
scipy = Image("scipy.png")
stickFigure = Shape("stick_figure.svg", aspect_ratio=10./25)
worldMap = Image("world.png", aspect_ratio=901./491)
