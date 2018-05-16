import img


## To handle DPI
## NOTE: the printer could not handle the 300DPI file so we went to 125.
class Screen(object):
    DPI = 125  # The default for PDFs are actually 72 DPI though.
    @classmethod
    def points(cls, pointsize):
        return int(pointsize * cls.DPI / 72.)
    @classmethod
    def inches(cls, i):
        return i * cls.DPI * 1.
    def __init__(self, width, height):
        self.width = int(Screen.DPI * width)
        self.height = int(Screen.DPI * height)


## To map object domain to pixel range
class PixRange(object):
    def __init__(self, from_range, to_range, transform=None):
        self._transform = (lambda x: x) if transform is None else transform
        self._domain = [self._transform(x) for x in from_range]
        self.domain = from_range
        self.pixel_range = to_range
        num = self.pixel_range[1] - self.pixel_range[0]
        den = self._domain[1] - self._domain[0]
        self.slope =  num * 1.0 / den
        
    def clip(self, value):
        return min(max(value, min(self.pixel_range)), max(self.pixel_range))

    def __call__(self, value):
        v = self.pixel_range[0] + (self._transform(value) - self._domain[0]) * self.slope
        return self.clip(v)


## World Map
def draw_map(x, y, conferences, map_width=None, map_height=None):
    imageMode(CENTER)
    textAlign(LEFT)
    pt_sz = Screen.points(16)
    textSize(pt_sz)
    if map_width is None and map_height is None:
        map_width = Screen.inches(3.)
        map_height = map_width / img.worldMap.aspect_ratio
    elif map_width and not map_height:        
        map_height = map_width / img.worldMap.ratio
    elif map_width is None:
        map_width = map_height * img.worldMap.ratio
    img.worldMap.put(x, y, map_width, map_height)
    if conferences is None:
        text('To be continued ...', x - map_width / 4., y)
        return
    for conf, loc in conferences:
        imageMode(CENTER)
        # These strange offsets are because I scaled the map and cropped it
        # separately from projecting the lat,lon of the cities to the same
        # x,y space...and didn't want to redo the map later. Sorry.
        xx = x - map_width/2. + (loc[0]-57) * map_width/843.  # 59; 842
        yy = y - map_height/2. + (loc[1]-48) * map_height/465  # 48; 465
        #text(conf, xx, yy)
        if 'Django' in conf:
            img.django.put(xx, yy, pt_sz * .8)
        elif 'PyData' in conf:
            img.pydata.put(xx, yy, pt_sz * .7)
        elif 'SciPy' in conf:
            img.scipy.put(xx, yy, pt_sz * .8)
        elif 'Plone' in conf:
            img.plone.put(xx, yy, pt_sz * .8)
        elif conf == 'PyCon' or conf == 'EuroPyCon' or conf == 'PyCon APAC':
            img.pycon.put(xx, yy, pt_sz * 1.1)
        else:
            text('+', xx, yy)


## Little people icons
def draw_cluster(x_ctr, y_ctr, n_icons, icon,
                 icon_width=42,
                 icon_height=104,
                 left=None,
                 right=None,
                 top=None,
                 bottom=None):
    """Draw a cluster of `n_icons` icons, centered around x_ctr, y_ctr.
    
    If the left, right, top, or bottom bounds are non-null, constrain
    the cluster to not extend beyond those bounds.
    """
    max_ncol = int((right - left)/icon_width) if right and left else None
    max_nrow = int((bottom - top)/icon_height) if top and bottom else None
    # Handle the overconstrained cluster
    if max_ncol and max_nrow:
        if max_ncol * max_nrow < n_icons:
            raise ValueError("draw_cluster: Cluster can't fit in the given bounds.")
    #ideal_ncol = 1 + ceil(sqrt(n_icons) * icon_height / icon_width / 1.68)
    ideal_ncol = n_icons if n_icons < 6 else 5 if n_icons < 11 else 10
    ideal_nrow = ceil(n_icons * 1.0 / ideal_ncol)
    if max_nrow and max_nrow < ideal_nrow:
        nrow = max_nrow
        ncol = int(ceil(n_icons * 1.0 / nrow))
    elif max_ncol and max_ncol < ideal_ncol:
        ncol = max_ncol
        nrow = int(ceil(n_icons * 1.0 / ncol))
    else:
        ncol = int(ideal_ncol)
        nrow = int(ideal_nrow)
    h_step = icon_width / 2
    v_step = icon_height / 2
    x_left = left if left else right - icon_width * ncol if right else x_ctr - icon_width * ncol/2. 
    y_top = top if top else bottom - icon_height * nrow if bottom else y_ctr - icon_height * nrow/2.
    remainder = int(n_icons % ncol)
    # The first row is incomplete
    extra = 1 if remainder else 0
    for i in range(remainder):
        icon.put(x_left + (ncol - remainder + i) * icon_width, y_top, icon_width, icon_height)
        #shape(icon, x_left + (ncol - remainder + i) * icon_width, y_top, icon_width, icon_height)
    for j in range(int(n_icons/ncol)):
        for i in range(ncol):
            icon.put(x_left + i * icon_width, y_top + (j+extra) * icon_height, icon_width, icon_height)
            #shape(icon, x_left + i * icon_width, y_top + (j+extra) * icon_height, icon_width, icon_height)


def draw_edge(xy1, xy2, ct, xoffset=Screen.inches(.3)):
    noFill()
    alpha = 42 if ct > 1 else 10
    stroke(color(88, alpha))
    strokeWeight(ct / 2.)
    midy = (xy1[1] + xy2[1]) / 2.
    dx = xoffset * atan(abs(xy2[1]-xy1[1])/200)
    bezier(xy1[0], xy1[1], xy1[0] - dx, midy, xy2[0] - dx, midy, xy2[0], xy2[1])


def draw_bar(x0, y0, categories, sorted_cats, ct2sqinch=.5, wd_in=2.42):
    area = sum(s['n'] for k,c in categories.items() for s in c.values() if k != 'Keynotes')
    wd = Screen.inches(wd_in)
    ht = Screen.inches(area * ct2sqinch / wd_in)
    noStroke()
    y = y0
    cat_positions = {}
    subcat_positions = {}
    for cat, col in img.COLORS.items():
        if cat not in categories:
            continue
        ct = sum(s['n'] for s in categories[cat].values())
        fill(*col)
        ht = Screen.inches(ct * ct2sqinch / wd_in)
        highlight_rect(x0 - wd/2., y-ht, wd, ht, color(*col))
        cat_positions[cat] = y-ht
        mul = 2.
        padding = (ht - Screen.points(9 * len(categories[cat]) + mul * ct)) / (1 + len(categories[cat]))
        yy = y - padding
        xx = x0 - wd/2. + Screen.points(3)
        for subcat in sorted_cats[cat]:
            if subcat not in categories[cat]:
                continue
            lookup = categories[cat][subcat]
            fill(0, 0, 0)
            textAlign(LEFT)
            textSize(Screen.points(9 + mul * lookup['n']))
            t = text(subcat, xx, yy)
            subcat_positions[subcat] = (xx, yy)
            yy = yy - Screen.points(9 + mul * lookup['n']) - padding
        y = y - ht
    # Add captions
    stroke(0)
    strokeWeight(Screen.points(1))
    pt = Screen.points(11)
    leading = 1.3 * pt
    textSize(pt)
    textLeading(leading)
    caption_bottom = y - 1.25 * pt
    caption_left = xx - Screen.points(3)
    linked = False
    for cat in reversed(img.COLORS):
        col = img.COLORS[cat]
        if cat not in categories:
            continue
        for subcat in reversed(sorted_cats[cat]):
            if subcat not in categories[cat]:
                continue
            xx, yy = (a - Screen.points(9)/2. for a in subcat_positions[subcat])
            if 'caption' in categories[cat][subcat]:
                caption_left -= 0 if linked else pt * 1.2
                linked = False
                caption = categories[cat][subcat]['caption']
                text_ht = leading * get_nrows(caption, wd * 1.1)
                pen([(xx, yy), (caption_left, yy), (caption_left, caption_bottom - pt/2.)], weight=Screen.points(1), squig=.2)
                text(caption, caption_left - pt/4., caption_bottom - text_ht - pt/2., wd * 1.1, text_ht + pt)
                caption_bottom -= text_ht + 1.5 * leading
            elif 'link_caption' in categories[cat][subcat]:
                if not linked:
                    linked = True
                    caption_left -= pt * 1.2
                pen([(xx, yy), (caption_left - pt/2., yy)], weight=Screen.points(1), squig=.2)
    return cat_positions



# -------------------------------------------- Hand drawing tools
# See: Zainab Faisal Al-Meraj et. al. "Mimicking human-drawn pencil lines"
#      https://dspace.library.uvic.ca/handle/1828/1018
def squiggle(squig=1):
    return (Screen.inches(squig/72.) * random(-5., 5.) for i in range(2))

def make_path(p0, pf, extra=lambda x: 0):
    mul = 1  #Screen.DPI / 72.
    def path(tau):
        return p0 + (p0 - pf) * mul * (15. * tau - 6. * tau**2 - 10) * tau**3 + extra(tau)
    return path


def pen(xypairs, weight=Screen.points(2), squig=1, color=color(0)):
    noFill()
    strokeWeight(weight)
    stroke(color)
    x0, y0 = xypairs[0]
    xf, yf = xypairs[-1]
    beginShape()
    curveVertex(x0, y0)
    for xypair in zip(xypairs, xypairs[1:]):
        x1, y1 = xypair[0]
        x2, y2 = xypair[1]
        x = make_path(x1, x2)
        y = make_path(y1, y2)
        d = sqrt((x2-x1)**2 + (y2-y1)**2)
        if d <= Screen.points(200):
            delta = .25
        elif d <= Screen.points(400):
            delta = .125
        else:
            delta = .1    
        for t in range(int(1/delta)):
            tau = t * delta
            dx, dy = (0, 0) if t == 0 or t == int(1/delta) else squiggle(squig)
            curveVertex(x(tau) + dx, y(tau) + dy)
    curveVertex(xf, yf)
    endShape()


def highlight(x0, y0, xf, yf, col, w=Screen.points(20)):
    noFill()
    strokeWeight(Screen.points(4))
    white = color(255)
    theta = atan2(yf-y0, xf-x0) + HALF_PI
    wx = w * cos(theta) / 2
    wy = w * sin(theta) / 2
    x = make_path(x0, xf)
    y = make_path(y0, yf, extra=lambda tau:5 * (tau**2 - tau))
    d = max(abs(xf-x0), abs(yf-y0))
    for t in range(int(d)):
        tau = map(t, 0, d, 0, 1)
        c = lerpColor(col, white, 2*(tau - tau**2))
        stroke(c, 142)
        xx = x(tau)
        yy = y(tau)
        line(xx-wx, yy-wy, xx+wx, yy+wy)


def highlight_rect(x0, y0, wd, ht, col, highlighter_wd=Screen.points(16)):
    xf = x0 + wd
    yf = y0 + ht
    highlighter_wd = min(highlighter_wd, ht)
    y0 += highlighter_wd / 2
    yf -= highlighter_wd / 2
    y = y0
    n_strokes = floor(ht * 1.1 / highlighter_wd)
    for i in range(n_strokes):
        dy = i * .9 * highlighter_wd
        if i == 0:
            dx0 = dxf = dy0 = dyf = 0
        else:
            dx0 = random(-.05, 0.02) * highlighter_wd
            dxf = random(-.02, 0.05) * highlighter_wd
            dy0 = random(-.15, .15) * highlighter_wd
            dyf = random(-.15, .15) * highlighter_wd
        highlight(x0+dx0, min(y+dy+dy0, yf), xf+dxf, min(y+dy+dyf, yf), col, highlighter_wd)
    highlight(x0, yf, xf, yf, col, highlighter_wd)


# -------------------------------------------- Text wrapping calculator
def get_nrows(msg, wd):
    words = msg.split()
    rows = ['']
    for word in words:
        tmp = '{} {}'.format(rows[-1], word)
        if textWidth(tmp) < wd:
            rows[-1] = tmp
        else:
            rows.append(word)
    return len(rows)
