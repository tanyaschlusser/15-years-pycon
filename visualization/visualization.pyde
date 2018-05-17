import datetime
import math
from random import randint

# my libraries
import datasets
import img
import util

add_library('pdf')
# This has to be loaded after the screen/pdf is created
xkcdFont = None

# Typical poster is 48" x 36".
# Default DPI for PDF is 72 ... need to change all sizes when going --> 125 DPI
util.Screen.DPI = 72  #125
poster = util.Screen(66, 40)


# Possibly don't need this because of Processing push/pop options
# but I'm new to Processing.
def reset_when_done(fun):
    def wrapped(*args, **kwargs):
        fun(*args, **kwargs)
        fill(0)
        stroke(0)
        strokeWeight(util.Screen.points(1))
        strokeCap(SQUARE)
        textAlign(CENTER)
        textSize(util.Screen.points(18))
    return wrapped


@reset_when_done
def setup():
    global xkcdFont
    size(poster.width, poster.height, PDF,
         "poster.pdf" if util.Screen.DPI == 72 else "poster_{}dpi.pdf".format(util.Screen.DPI)
    )
    print('Poster width: {}, height:{}'.format(poster.width, poster.height))
    background(255)
    xkcdFont = createFont("xkcd-script.ttf", util.Screen.points(18))
    textFont(xkcdFont)


# `x` is a function mapping a date to an x position, given a range.
#     It copies Mike Bostock's same style of doing things in d3.
x = util.PixRange(
    (datetime.date(2002,7,1), datetime.date(2019,7,1)),
    (util.Screen.inches(.8), poster.width - util.Screen.inches(1.5)),
    transform = lambda x: x.toordinal()
)


@reset_when_done
def make_citations(citations, y):
    textSize(util.Screen.points(14))
    textAlign(LEFT)
    text(citations, util.Screen.inches(.51), y)


@reset_when_done
def make_title(y):
    pt = util.Screen.points(120)
    textSize(pt)
    xx = util.Screen.inches(1.6)
    textAlign(LEFT)
    text("15 16 Years of PyCon", xx * .99, y)
    # Now 'x' over the 15 since we miffed that one. Lol.
    dx = .2 * pt
    dy = .15 * pt
    wt = util.Screen.points(9)
    util.pen([(xx - dx, y + dy - pt), (xx - dx + pt, y + dy)], weight=wt, squig=1)
    util.pen([(xx - dx, y + dy), (xx - dx + pt, y + dy - pt)], weight=wt, squig=1)
    y += pt * .75
    textSize(pt / 2)
    text("Tanya Schlusser and Hailey Hoyat", xx * .99, y)


@reset_when_done
def make_notes(y):
    pt = util.Screen.points(20)
    xx = util.Screen.inches(2)
    textSize(pt)
    textLeading(1.42 * pt)
    textAlign(LEFT)
    wd = util.Screen.inches(8)
    text(datasets.notes.split('\n\n')[0], xx, y, wd, util.Screen.inches(8.5))


@reset_when_done
def make_keynotes(keynotes, y, ht=util.Screen.inches(4)):
    one_year = x(datetime.date(2011, 1, 1)) - x(datetime.date(2010, 1, 1))
    pt = util.Screen.points(13)
    textSize(pt)
    textLeading(1.42 * pt)
    textAlign(LEFT, TOP)
    wd = one_year * .9
    for con in sorted(datasets.pycon_dates, key=lambda x: x['begin_date']):
        mid_dt = con['begin_date'] + (con['begin_date'] - con['end_date'])/2
        mid_dt = datetime.date(mid_dt.year, 4, 16)
        desc = keynotes[mid_dt.year]
        text(desc, x(mid_dt) - wd/2., y, wd, ht)
        

@reset_when_done
def make_pycon_timeline(pycons, y):
    textAlign(CENTER, CENTER)
    for con in pycons:
        # attendees, sponsors, volunteers, speakers
        # conf, begin_date, end_date, city
        # Highlight the dates of the conference
        mid_dt = con['begin_date'] + (con['begin_date'] - con['end_date'])/2
        util.highlight(x(con['begin_date']), y, x(con['end_date']), y,
                       color(*img.COLORS['Community']),
                       w=util.Screen.points(12))
        month_year = mid_dt.strftime('%B %Y')
        mid_dt = datetime.date(mid_dt.year, 4, 16)
        textSize(util.Screen.points(18))
        text(con['city'], x(mid_dt), y - util.Screen.points(50))
        textSize(util.Screen.points(24))
        text(month_year, x(mid_dt), y - util.Screen.points(28))
        textSize(util.Screen.points(20))
        # Volunteers, sponsors, speakers
        tmp = 's' * int(round(con['speakers'] / 10.))
        text(tmp, x(mid_dt), y - util.Screen.points(124))
        tmp = '$' * int(round(con['sponsors'] / 10.))
        text(tmp, x(mid_dt), y - util.Screen.points(101))  
        tmp = 'v' * int(round(con['volunteers'] / 10.))
        text(tmp, x(mid_dt), y - util.Screen.points(79)) 
        n_figures = math.ceil(con['attendees'] / 100.)
        util.draw_cluster(x(mid_dt), y - util.Screen.points(155), n_figures,
                          icon=img.stickFigure,
                          icon_width=util.Screen.points(10),
                          icon_height=util.Screen.points(25),
                          bottom=y - util.Screen.points(140))  # previously `y`
    util.pen([(x(x.domain[0]), y), (x(x.domain[1]), y)], weight=util.Screen.points(1), squig=.5)
    yy = y - util.Screen.inches(2.15)
    dy = util.Screen.points(28)
    legend(' = 100 attendees', yy, img=img.stickFigure, yoffset=-.4, img_scale=.6, pointsize=20)
    legend(' s = 10 speakers', yy + dy * 1, pointsize=20)
    legend(' $ = 10 sponsors', yy + dy * 2, pointsize=20)
    legend(' v = 10 volunteer leads', yy + dy * 3, pointsize=20)
        

@reset_when_done
def make_conference_maps(confs_by_year, y):
    for con in sorted(datasets.pycon_dates, key=lambda x: x['begin_date']):
        mid_dt = con['begin_date'] + (con['begin_date'] - con['end_date'])/2
        yr = str(mid_dt.year)
        mid_dt = datetime.date(mid_dt.year, 4, 16)
        confs = None if yr not in confs_by_year else confs_by_year[yr]
        util.draw_map(x(mid_dt), y, confs, map_width=util.Screen.inches(3.8))
    ## NOTE: Visitors to the poster recommended moving the legend to the
    ##       left-hand side *before* the chart starts so they don't have to walk
    ##       all the way to the other side
    # Legend
    yy = y - util.Screen.inches(.95)
    dy = util.Screen.inches(.34)
    legend(" = DjangoCon", yy, img=img.django, yoffset=.25, pointsize=18)
    legend(' = PyData conference', yy + dy, img=img.pydata, yoffset=-.2, pointsize=18, img_scale=.8)
    legend(' = SciPy conference', yy + dy * 2.1, img=img.scipy, yoffset=.3, pointsize=18)
    legend(' = Plone conference', yy + dy * 3.1, img=img.plone, yoffset=.2, pointsize=18)
    legend(' = regional PyCon', yy + dy * 4.1, img=img.pycon, yoffset=.3, pointsize=18)
    legend(' + = local PyCon', yy + dy * 5.1, pointsize=18)


@reset_when_done
def make_map_annotations(y):
    # circle the location
    # line down to text
    # 2015 -- Ukraine
    dymul = .95
    dkred = color(142, 0, 10)
    r = util.Screen.points(25)
    xx, yy = x(datetime.date(2015, 4, 1)) + util.Screen.points(12), y - util.Screen.points(30)
    circle = [(xx - r * 1.1 * cos(HALF_PI / 4. * i), yy + r*sin(HALF_PI / 4. * i)) for i in range(17)]
    dy = util.Screen.inches(3.7)  # 3.92
    dx = util.Screen.inches(.8)
    dropdown = [(xx - 1.1 * r, yy), (xx - 1.1 * r, yy + dy), (xx - r + dx, yy + dy)]
    util.pen(circle + dropdown, weight=util.Screen.points(1), squig=.1, color=dkred)
    fill(dkred)
    textAlign(LEFT, CENTER)
    text('PyCon Ukraine not held - they helped with PyCon Poland.', xx - r + dx + util.Screen.points(7), yy + dy)
    pushMatrix()
    translate(xx - r - util.Screen.inches(.08), yy + dymul * dy + util.Screen.inches(.37))
    rotate(.26)
    img.heart.put(0, 0, width=util.Screen.inches(.28))
    popMatrix()
    # 2017 -- Singapore
    r = util.Screen.points(12)
    xx, yy = x(datetime.date(2017, 5, 1)) + util.Screen.points(62), y + util.Screen.points(18)
    circle = [(xx + r * 1.02 * sin(HALF_PI / 3. * i), yy + r*cos(HALF_PI / 3. * i)) for i in range(13)]
    #dy = util.Screen.inches(3.8)
    dropdown = [(xx, yy+r), (xx, yy + dymul * dy), (xx - dx, yy + dymul * dy)]
    util.pen(circle + dropdown, weight=util.Screen.points(1), squig=.08, color=dkred)
    textAlign(RIGHT, CENTER)
    text('PyCon Singapore not held - they helped Malaysia with PyCon Asia Pacific.', xx - dx - util.Screen.points(6), yy + dymul * dy)
    pushMatrix()
    translate(xx - dx - util.Screen.inches(1.2), yy + dy - util.Screen.inches(.9))
    rotate(-.1)
    img.heart.put(0, 0, width=util.Screen.inches(.3))
    popMatrix()


@reset_when_done
def legend(msg, y, img=None, pointsize=14, yoffset=0, img_scale=1):
    pt = util.Screen.points(pointsize)
    xlegend = poster.width - util.Screen.inches(3.55)
    textSize(pt)
    textAlign(LEFT, TOP)
    dx = 0
    if img is not None:
        imageMode(CORNER)
        dx = pt * img_scale
        img.put(xlegend, y + dx * yoffset, dx)
    text(msg, xlegend + dx, y)


@reset_when_done
def make_history(hist, y, pt=util.Screen.points(16)):
    textAlign(LEFT)
    textSize(pt)
    xprev = 0
    yprev = 0
    y0 = y
    dy = 1.2 * pt
    pushMatrix()
    translate(util.Screen.inches(.51), y - 1.1 * dy)
    rotate(-.045)
    text('(Before 2003)', 0, 0)
    popMatrix()
    for dt, event, cat in hist:
        xx = x(dt)
        if xprev and xx < xprev and event not in ('Twisted', 'Jenkins', 'scikit-learn', 'Nvidia CUDA', 'Storm', 'Snowden leaks', 'HTML 5', 'Lektor'):
            y += dy
        else:
            y = y0
            xprev = 0
        w = textWidth(event)
        pad = pt * .03
        util.highlight(xx - 2 * pad, y - pt/2 + 4 * pad,
                       xx + w + 2 * pad, y - pt/2 + 4 * pad, 
                       col=color(*img.COLORS[cat]),
                       w=pt + pad)
        fill(0) 
        text(event, xx, y)
        xprev = max(xprev, xx + textWidth(event) * 1.05)
        yprev = y


@reset_when_done
def make_release_timeline(rels, y, version=2):
    textAlign(LEFT)
    for row in rels:
        if len(row.peps) == 0 or row.dt < x.domain[0] or not row.rel.startswith(str(version)):
            continue
        textSize(util.Screen.points(14))
        text(row.rel, x(row.dt), y + util.Screen.points(14))
        delta = 0
        for i in range(len(row.peps)):
            pep = row.peps[i]
            if pep == '':
                print("skipping i={} in pep {}".format(i, pep))
                delta = 5
            else:
                textSize(util.Screen.points(11))
                text("{}: {}".format(pep, datasets.pep_descs[pep]),
                     x(row.dt),
                     y + util.Screen.points(10*(i + 3) + delta))


@reset_when_done
def make_bars(conferences, sorted_cats, y):
    for con in sorted(datasets.pycon_dates, key=lambda x: x['begin_date']):
        print(con['conf'])
        mid_dt = con['begin_date'] + (con['begin_date'] - con['end_date'])/2
        # TANYA
        mid_dt = datetime.date(mid_dt.year, 4, 16)
        categories = conferences[str(mid_dt.year)]
        cat_positions = util.draw_bar(x(mid_dt), y, categories, sorted_cats)
    yy = y - util.Screen.inches(10)
    dy = util.Screen.inches(.5)
    for i, cat in enumerate(reversed(img.COLORS)):
        noStroke()
        xlegend = poster.width - util.Screen.inches(3.55)
        util.highlight_rect(xlegend, cat_positions[cat], util.Screen.inches(1.5), util.Screen.points(20), color(*img.COLORS[cat]))
        fill(0)
        if '/' in cat:
            tmp = cat.split('/')
            for j, c in enumerate(tmp):
                extra = ' /' if j + 1 < len(tmp) else ''
                legend(c + extra, cat_positions[cat] + (1 + j) * util.Screen.points(20), pointsize=20)
        elif ' ' in cat:
            tmp = cat.split()
            for j, c in enumerate(tmp):
                legend(c, cat_positions[cat] + (1 + j) * util.Screen.points(20), pointsize=20)
        else:
            legend(cat, cat_positions[cat] + util.Screen.points(20), pointsize=20)



def draw():
    make_title(util.Screen.inches(2.5))
    make_notes(util.Screen.inches(4.8))
    textAlign(CENTER, TOP)
    y = util.Screen.inches(34.55)
    make_conference_maps(datasets.world_conferences, y)
    make_map_annotations(y)
    y = util.Screen.inches(30.54)
    make_keynotes(datasets.keynotes, y)
    legend('Keynotes', y, pointsize=20)
    y = util.Screen.inches(30.32)
    make_pycon_timeline(datasets.pycon_dates, y)
    y = util.Screen.inches(26.8)
    make_bars(datasets.graph, datasets.sorted_cats, y)
    y = util.Screen.inches(36.128)
    make_history(datasets.history, y)
    legend('Historical events', y, pointsize=20)
    #make_release_timeline(datasets.rel_to_peps, y)
    #legend('Python 2 releases', y)
    #y = height * .93  # .92
    #make_release_timeline(datasets.rel_to_peps, y, version=3)
    #legend('Python 3 releases', y)
    y = height - util.Screen.inches(.65)
    make_citations(datasets.citations, y)
    exit()
    print('Done')
