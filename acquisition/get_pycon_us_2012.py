import datetime
import re
import requests
from lxml import html

from data import database as db
from data.database import Conference, Talk, Human, Organization, Topic


# helpers 
org_matcher = re.compile("(?<=\().+(?=\))")
separators = re.compile('[,|/;]')


# Add this conference
YEAR = 2012
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Santa Clara, CA',
        country = 'USA',
        url = 'http://us.pycon.org/2012/about/',
        begin_date = datetime.date(YEAR, 3, 7),
        end_date = datetime.date(YEAR, 3, 15)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
# Get the conference details from the Wayback machine
response = requests.get(conference.url)
root = html.fromstring(response.text)

## Sponsors
xpath = '//div[@class="sponsors-side"]//img/@alt'
for alt in root.xpath(xpath):
    if not alt.lower() == 'net-ng':
        sponsor_name = alt.rsplit('-', 1)[0].strip()
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()


## Volunteers
url = 'https://us.pycon.org/2012/about/staff/'
xpath = '//div[@class="page"]//tr/td[2]'
print('volunteers')
print(url)
for volunteer_name in html.fromstring(requests.get(url).text).xpath(xpath):
    volunteer_name =  volunteer_name.text_content().strip('\n )') #volunteer_name.text_content().strip()
    if len(volunteer_name) == 0:
        continue
    if volunteer_name.startswith('Too many'):
        continue
    # There can be multiple comma-separated names.
    for name in re.split("[,&/]", volunteer_name):
        new_name = " ".join(n.strip(' (-') for n in name.split() if not "@" in n)
        if new_name and len(new_name) > 1:
            if '.' in new_name:
                new_name = " ".join(name.strip().split()[:3])
            volunteer = db.fetch_or_add(Human(name=new_name))
            if conference not in volunteer.volunteering:
                volunteer.volunteering.append(conference)

db.session.commit()


## Talks
## ~~~~~~
##
## Keynotes
keynotes = (
    (['Paul Graham'], 'Frighteningly Ambitious Startup Ideas', ['YCombinator'], 'http://pyvideo.org/pycon-us-2012/keynote-paul-graham-ycombinator.html'),
    (['Stormy Peters'], 'Growing the web community and the Python community', ['Mozilla'], 'http://pyvideo.org/pycon-us-2012/keynote-stormy-peters-mozilla-corporation.html'),
    (['David Beazley'], 'Tinkering with PyPy', [], 'http://pyvideo.org/pycon-us-2012/keynote-david-beazley.html'),
    (['Guido van Rossum'], 'Addressing common questions about Python', [], 'http://pyvideo.org/pycon-us-2012/keynote-guido-van-rossum.html')
)
for speaker_names, title, org, url in keynotes:
    talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
    talk.title = title
    talk.video_url = url
    data = db.TalkData(speaker_names, [], [])
    db.add_talk(talk, **data._asdict())


## Startup Series
url = 'https://us.pycon.org/2012/community/startuprow/'
xpath = '//div[@class="page"]/*'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
first_talk = next(i for i,e in enumerate(entries) if e.tag == 'h2')
i = first_talk + 1
print('startup row')
print(url)
while i < len(entries):
    e = entries[i]
    i += 1
    if e.tag == 'p':
        title = e.findtext('./a')
        if not title:
            continue
        talk = Talk(
            category=Talk.PLENARY, 
            conference_id=conference.id,
            title=title,
            abstract=e.text_content())
        data = db.TalkData([], ["startup row"], [talk.title])
        db.add_talk(talk, **data._asdict())

## Tutorials
##  ==> Ignore these...the links are broken and only the presenters'
##      last names are given, so it is hard to create an entry.
##
url = 'https://us.pycon.org/2012/schedule/tutorials/'
xpath = '//div[@class="presentation"]'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('tutorials')
print(url)
## Iterate through and extract the relevant content
for e in entries:
    a = e.find('./div[@class="title"]/a')
    title = a.text
    root = html.fromstring(requests.get('https://us.pycon.org'+a.get('href')).text)
    abstract = root.xpath('//div[@class="abstract"]')[0].text_content()
    speakers = root.xpath('//div[@class="speakers"]')[0].text_content().strip().split(',')
    _, level, category = root.xpath('//dl/dd/text()')
    level = 'Beginner' if level == 'Novice' else level
    talk = Talk(category=Talk.TUTORIAL, conference_id=conference.id, title=title)
    data = db.TalkData(speakers, [category], [])
    talk.abstract = abstract[:10000]
    talk.level = level
    db.add_talk(talk, **data._asdict())


url = 'https://us.pycon.org/2012/schedule/'
xpath = '//section[@id="body"]/div/*'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
first_talk = next(i for i,e in enumerate(entries) if e.tag == 'h2' and e.text == 'Friday')
i = first_talk + 1
print('talks')
print(url)
## Iterate through and extract the relevant content
for table in entries[i:]:
    if table.tag != 'table':
        continue
    for e in table.xpath('.//td[contains(@class, "presentation")]'):
        a = e.find('./div[@class="title"]/a')
        title = a.text
        if 'canceled' in title.lower():
            continue
        root = html.fromstring(requests.get('https://us.pycon.org'+a.get('href')).text)
        speakers = root.xpath('//div[@class="speakers"]/a/text()')
        abstract = root.xpath('//div[@class="abstract"]')[0].text_content()
        try:
            _, level, category = root.xpath('//dl/dd/text()')
        except ValueError:
            continue
        level = 'Beginner' if level == 'Novice' else level
        talk = Talk(category=Talk.TALK, conference_id=conference.id, title=title)
        data = db.TalkData(speakers, [category], [])
        talk.abstract = abstract[:10000]
        talk.level = level
        db.add_talk(talk, **data._asdict())


# Posters
url = 'https://us.pycon.org/2012/schedule/lists/posters/'
xpath = '//div[@class="session"]/div/a'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('posters')
print(url)
for a in entries:
    title = a.text
    if 'canceled' in title.lower():
        continue
    root = html.fromstring(requests.get('https://us.pycon.org'+a.get('href')).text)
    speakers = [
            s if not s.startswith(' and') else s[4:] 
            for ss in root.xpath('//div[@class="speakers"]/a/text()')
            for s in ss.split(',')
            if s != '?']
    abstract = root.xpath('//div[@class="abstract"]')[0].text_content()
    try:
        _, level, category = root.xpath('//dl/dd/text()')
    except ValueError:
        continue
    level = 'Beginner' if level == 'Novice' else level
    talk = Talk(category=Talk.POSTER, conference_id=conference.id, title=title)
    data = db.TalkData(speakers, [category], [])
    talk.abstract = abstract[:10000]
    talk.level = level
    db.add_talk(talk, **data._asdict())
