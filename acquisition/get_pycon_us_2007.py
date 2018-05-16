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
YEAR = 2007
wayback = 'https://web.archive.org/web/20070205022757/'
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Addison (near Dallas), TX',
        country = 'USA',
        url = wayback + 'http://us.pycon.org/TX2007/HomePage',
        begin_date = datetime.date(YEAR, 2, 22),
        end_date = datetime.date(YEAR, 3, 1)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
# Get the conference details from the Wayback machine
response = requests.get(conference.url)
root = html.fromstring(response.text)

## Sponsors
xpath = '//div[@id="sponsorlist"]//img/@title'
for sponsor_name in root.xpath(xpath):
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()

## Volunteers
wayback = 'https://web.archive.org/web/20070207091530/'
url = wayback + 'http://us.pycon.org:80/TX2007/DeptHeads'
xpath = '//div[@id="wikitext"]//table/tr/td[2]'
print('volunteers')
print(url)
for volunteer_name in html.fromstring(requests.get(url).text).xpath(xpath):
    volunteer_name = volunteer_name.text_content().strip()
    if len(volunteer_name) == 0:
        continue
    # There can be multiple comma-separated names.
    for name in volunteer_name.split(','):
        volunteer = db.fetch_or_add(Human(name=name))
        if conference not in volunteer.volunteering:
            volunteer.volunteering.append(conference)

db.session.commit()

## Talks
talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
data = db.TalkData([], [], [])
wayback = 'https://web.archive.org/web/20070207091801/'
url = wayback + 'http://us.pycon.org:80/TX2007/Keynotes'
xpath = '//div[@id="wikitext"]/*'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
first_talk = next(i for i,e in enumerate(entries) if e.tag == 'h2')
entries = entries[first_talk:-1]
print('talks')
print(url)
for e in entries:
    if e.tag == 'h2':
        if talk.title is not None:
            # Finished one.
            db.add_talk(talk, **data._asdict())
            data = db.TalkData([], [], [])
            talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
        speaker = e.text_content().split('(')[0].strip()
        data.speaker_names.extend(separators.split(speaker))
    elif e.tag == 'p' and e.text_content().startswith('Topic'):
        talk.title = e.text_content().split(' ', 1)[-1].strip().strip('"')

# don't forget the last one..
if talk.title is not None:
    db.add_talk(talk, **data._asdict())


# Tutorials
talk = Talk(category=Talk.TUTORIAL, conference_id=conference.id)
data = db.TalkData([], [], [])
wayback = 'https://web.archive.org/web/20070205022526/'
url = wayback + 'http://us.pycon.org:80/TX2007/Tutorials'
xpath = '//div[@id="wikitext"]/*'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
header = next(i for i,e in enumerate(entries) if e.tag == 'h2')
entries = entries[header+1:-1]
# Iterate through and extract the relevenant content
print('tutorials')
print(url)
for e in entries:
    if e.tag == 'p':
        if talk.title is not None:
            # Finished one.
            db.add_talk(talk, **data._asdict())
            talk = Talk(category=Talk.TUTORIAL, conference_id=conference.id)
            data = db.TalkData([], [], [])
        topic_header = e.text_content().split(':', 1)[0]
        data.topic_names.extend(topic_header.strip().split(' and '))
    elif e.tag == 'ul':
        for li in e.xpath('./li'):
            title = li.text_content()
            if 'CANCELLED' not in title:
                title, speaker = title.split(':', 1)[-1].strip().split(' by ')
                talk.title = title
                data.speaker_names.extend(separators.split(speaker))

# don't forget the last one..
if talk.title is not None:
    db.add_talk(talk, **data._asdict())


talk = Talk(category=Talk.TALK, conference_id=conference.id)
data = db.TalkData([], [], [])
wayback = 'https://web.archive.org/web/20070213073856/'
url = wayback + 'http://us.pycon.org:80/apps07/talks/'
xpath = '//*[contains(@class, "proposal_list_summary")]/*[not(self::br)]'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('talks')
print(url)
for e in entries:
    if e.tag == 'h2':
        if talk.title is not None:
            # Finished one
            db.add_talk(talk, **data._asdict())
            talk = Talk(category=Talk.TALK, conference_id=conference.id)
            data = db.TalkData([], [], [])
        talk.title = e.text_content().split('.', 1)[-1].strip()
    elif e.tag == 'div':
        talk.abstract = e.text_content().strip()
    else:  # span...
        tc = e.text_content()
        if tc.endswith('audio and materials)'):
            talk.level = tc.split()[1]
        elif tc.startswith('categories'):
            data.topic_names.extend(tc.split(':')[-1].split(','))
        else:  # Speaker names
            speaker = tc.strip('; ').split('(', 1)[0]
            data.speaker_names.extend(separators.split(speaker))
            data.organization_names.extend(org_matcher.findall(tc))

# don't forget the last one..
if talk.title is not None:
    db.add_talk(talk, **data._asdict())
