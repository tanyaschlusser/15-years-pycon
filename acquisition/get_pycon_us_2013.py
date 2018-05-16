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
YEAR = 2013
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Santa Clara, CA',
        country = 'USA',
        url = 'http://us.pycon.org/2013/',
        begin_date = datetime.date(YEAR, 3, 13),
        end_date = datetime.date(YEAR, 3, 21)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
url = 'https://us.pycon.org/2013/sponsors/'
response = requests.get(url)
root = html.fromstring(response.text)

## Sponsors
xpath = '//div[@class="sponsor"]//img/@alt'
for alt in root.xpath(xpath):
    if not alt.lower() == 'net-ng':
        sponsor_name = alt.rsplit('-', 1)[0].strip()
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()


## Volunteers
url = 'https://us.pycon.org/2013/about/staff/'
xpath = '//div[@class="box-content"]//tr/td[2]'
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
        print(new_name)

db.session.commit()


## Talks
## ~~~~~~
##
## Keynotes
keynotes = (
    (['Eben Upton'], 'The Raspberry Pi: providing children around the world the opportunity to learn programming', ['Raspberry Pi Foundation'], 'http://pyvideo.org/pycon-us-2013/keynote-2.html', ['education']),
    (['Raymond Hettinger'], 'What makes Python Awesome', [], 'http://pyvideo.org/pycon-us-2013/keynote-3.html', ['core']),
    #(['Jessica McKellar'], 'How the Internet works', [], 'http://pyvideo.org/pycon-us-2013/how-the-internet-works.html', ['web', 'twisted', 'scapy']),
    (['Guido van Rossum'], 'Announcing asyncio for the standard library (PEP 3156)', [], 'http://pyvideo.org/pycon-us-2013/keynote-1.html', ['concurrency', 'standard library'])
)
for speaker_names, title, org, url, topics in keynotes:
    talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
    talk.title = title
    talk.video_url = url
    data = db.TalkData(speaker_names, topics, org)
    db.add_talk(talk, **data._asdict())



## Tutorials
##  ==> Ignore these...the links are broken and only the presenters'
##      last names are given, so it is hard to create an entry.
##
url = 'https://us.pycon.org/2013/schedule/tutorials/list/'
xpath = '//div[contains(@class,"presentation")]'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('tutorials')
print(url)
## Iterate through and extract the relevant content
for e in entries:
    a = e.find('./h3/a')
    title = a.text
    root = html.fromstring(requests.get('https://us.pycon.org'+a.get('href')).text)
    abstract = root.xpath('//div[@class="abstract"]')[0].text_content()
    speakers = root.xpath('//h4/a/text()')
    level, category = root.xpath('//dl/dd/text()')
    level = 'Beginner' if level == 'Novice' else level
    talk = Talk(category=Talk.TUTORIAL, conference_id=conference.id, title=title)
    data = db.TalkData(speakers, [category], [])
    talk.abstract = abstract[:10000]
    talk.level = level
    db.add_talk(talk, **data._asdict())


url = 'https://us.pycon.org/2013/schedule/talks/list/'
xpath = '//div[contains(@class,"presentation")]/h3/a'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('talks')
print(url)
# Iterate through and extract the relevant content
for a in entries:
    title = a.text
    if 'canceled' in title.lower():
        continue
    root = html.fromstring(requests.get('https://us.pycon.org'+a.get('href')).text)
    speakers = root.xpath('//h4/a/text()')
    abstract = root.xpath('//div[@class="abstract"]')[0].text_content()
    try:
        level, category = root.xpath('//dl/dd/text()')
    except ValueError:
        continue
    level = 'Beginner' if level == 'Novice' else level
    talk = Talk(category=Talk.TALK, conference_id=conference.id, title=title)
    data = db.TalkData(speakers, [category], [])
    talk.abstract = abstract[:10000]
    talk.level = level
    db.add_talk(talk, **data._asdict())


## Posters
url = 'https://us.pycon.org/2013/schedule/posters/list/'
xpath = '//div[contains(@class,"presentation")]/h3/a'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('posters')
print(url)
for a in entries:
    title = a.text
    if 'canceled' in title.lower():
        continue
    root = html.fromstring(requests.get('https://us.pycon.org'+a.get('href')).text)
    speakers = root.xpath('//h4/a/text()')
    try:
        abstract = root.xpath('//div[@class="abstract"]')[0].text_content()
        level, category = root.xpath('//dl/dd/text()')
    except (ValueError,  IndexError):
        continue
    level = 'Beginner' if level == 'Novice' else level
    talk = Talk(category=Talk.POSTER, conference_id=conference.id, title=title)
    data = db.TalkData(speakers, [category], [])
    talk.abstract = abstract[:10000]
    talk.level = level
    db.add_talk(talk, **data._asdict())
