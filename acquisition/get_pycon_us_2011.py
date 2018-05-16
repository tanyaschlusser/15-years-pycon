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
YEAR = 2011
wayback = 'https://web.archive.org/web/20110526124349/'
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Atlanta, GA',
        country = 'USA',
        url = wayback + 'http://us.pycon.org/2011/about/',
        begin_date = datetime.date(YEAR, 3, 9),
        end_date = datetime.date(YEAR, 3, 17)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
# Get the conference details from the Wayback machine
response = requests.get(conference.url)
root = html.fromstring(response.text)

## Sponsors
xpath = '//div[@id="right"]//img/@alt'
for alt in root.xpath(xpath):
    sponsor_name = alt.rsplit('-', 1)[0].strip()
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()


## Volunteers
wayback = 'https://web.archive.org/web/20110126022427/'
url = wayback + 'http://us.pycon.org:80/2011/about/staff/'
xpath = '//div[@id="main"]//tr/td[2]/text()'
print('volunteers')
print(url)
for volunteer_name in html.fromstring(requests.get(url).text).xpath(xpath):
    volunteer_name =  volunteer_name.strip('\n )') #volunteer_name.text_content().strip()
    if len(volunteer_name) == 0 or volunteer_name.startswith('('):
        continue
    if volunteer_name.lower().startswith("see the"):
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
    (['Hilary Mason'], 'Hello, PyCon'),
    (['Guido van Rossum'], 'A Fireside Chat with Guido van Rossum')
)
for speaker_names, title in keynotes:
    talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
    talk.title = title
    data = db.TalkData(speaker_names, [], [])
    db.add_talk(talk, **data._asdict())


## Startup Series
talk = Talk(category=Talk.PLENARY, conference_id=conference.id)
data = db.TalkData([], ['startup'], [])
wayback = 'https://web.archive.org/web/20110316093256/'
url = wayback + 'http://us.pycon.org:80/2011/home/keynotes/'
xpath = '//div[@class="page"]/*'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
first_talk = next(i for i,e in enumerate(entries) if e.tag == 'h1' and e.text.startswith('Startup'))
entries = entries[first_talk+1:]
first_talk = next(i for i,e in enumerate(entries) if e.tag == 'h2')
i = first_talk
print('startup row')
print(url)
while i < len(entries):
    e = entries[i]
    i += 1
    if e.tag == 'h2':
        if talk.title:
            # new talk
            db.add_talk(talk, **data._asdict())
            talk = Talk(category=Talk.PLENARY, conference_id=conference.id)
        talk.title = e.text
        data = db.TalkData([], ["startup"], [])
    elif e.tag == 'ul':
        names = [n.split('-') for n in e.xpath('li/text()')]
        org = names[0][1].strip()
        people = [n[0].split(',')[0].strip() for n in names]
        data.speaker_names.extend(people)
        data.organization_names.append(org)
    else:
        if talk.abstract:
            talk.abstract = '\n'.join((talk.abstract, e.text))
        else:
            talk.abstract = e.text

# Last one
db.add_talk(talk, **data._asdict())

## Tutorials
##  ==> Ignore these...the links are broken and only the presenters'
##      last names are given, so it is hard to create an entry.
##
wayback = 'https://web.archive.org/web/20110112152542/'
url = wayback + 'http://us.pycon.org:80/2011/schedule/lists/tutorials/'
xpath = '//div[@class="session"]'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('tutorials')
print(url)
## Iterate through and extract the relevant content
for e in entries:
    a = e.find('./div[@class="title"]/a')
    title = a.text
    root = html.fromstring(requests.get('https://web.archive.org'+a.get('href')).text)
    abstract = root.xpath('//div[@class="abstract"]')[0].text_content()
    meta = e.findtext('./div[@class="metadata"]')
    level, speakers = [m.strip() for m in meta.split('Tutorial')]
    level = 'Beginner' if level == 'Novice' else level
    speakers = speakers.split('by', 1)[-1].split('with')
    talk = Talk(category=Talk.TUTORIAL, conference_id=conference.id)
    data = db.TalkData(speakers, [], [])
    talk.title = title
    talk.abstract = abstract[:10000]
    talk.level = level
    db.add_talk(talk, **data._asdict())


wayback = 'https://web.archive.org/web/20110112152611/'
url = wayback + 'http://us.pycon.org:80/2011/schedule/lists/talks/'
xpath = '//div[@class="session"]'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('talks')
print(url)
## Iterate through and extract the relevant content
for e in entries:
    a = e.find('./div[@class="title"]/a')
    title = a.text
    root = html.fromstring(requests.get('https://web.archive.org'+a.get('href')).text)
    abstract = root.xpath('//div[@class="abstract"]')[0].text_content()
    meta = e.findtext('./div[@class="metadata"]')
    try:
        level, speakers = [m.strip() for m in meta.split('Talk')]
        category = Talk.TALK
    except ValueError:
        level, speakers = [m.strip() for m in meta.split('Panel')]
        category = Talk.PANEL
    level = 'Beginner' if level == 'Novice' else level
    speakers = re.sub(',? \?', '', speakers)
    speakers = [s.strip() for s in speakers.split('by', 1)[-1].split('with')]
    if len(speakers) > 1:
        first_speaker, remaining_speakers = speakers
        speakers = [first_speaker] + [s for s in remaining_speakers.split(',') if len(s.strip())]
    talk = Talk(category=Talk.TALK, conference_id=conference.id)
    data = db.TalkData(speakers, [], [])
    talk.title = title
    talk.abstract = abstract[:10000]
    talk.level = level
    db.add_talk(talk, **data._asdict())
