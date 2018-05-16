import datetime
import re
import requests
from lxml import html

from data import database as db
from data.database import Conference, Talk, Human, Organization, Topic


# helpers 
org_matcher = re.compile("(?<=\().+(?=\))")
separators = re.compile('[,|/;]')

def find_first(arr, match_fun):
    """`next(i for i,e in enumerate(arr) if match_fun(e))`"""
    return next(i for i,e in enumerate(arr) if match_fun(e))


# Add this conference
YEAR = 2006
wayback = 'https://web.archive.org/web/20070208233907/'
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Addison (near Dallas), TX',
        country = 'USA',
        url = wayback + 'https://us.pycon.org/TX2006/HomePage',
        begin_date = datetime.date(YEAR, 2, 23),
        end_date = datetime.date(YEAR, 3, 2)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
# Get the conference details from the Wayback machine
response = requests.get(conference.url)
root = html.fromstring(response.text)

## Sponsors
print('sponsors')
xpath = '//td[@id="sponsors"]//img/@title'
for sponsor_name in root.xpath(xpath):
    print(sponsor_name)
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()

## Volunteers
wayback = 'https://web.archive.org/web/20070208233858/'
url = wayback + 'http://us.pycon.org:80/TX2006/DeptHeads'
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
first_talk = find_first(entries, lambda e: e.tag == 'h2')
#first_talk = next(i for i,e in enumerate(entries) if e.tag == 'h2')
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
wayback = ''
url = wayback + 'https://wiki.python.org/moin/PyCon2006/Tutorials'
xpath = '//div[@id="content"]//li'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('tutorials')
print(url)
# Iterate through and extract the relevenant content
for e in entries:
    title, speakers = e.text_content().rsplit(',', 1)
    if 'cancelled' in title.lower():
        continue
    talk = Talk(category=Talk.TUTORIAL, conference_id=conference.id)
    data = db.TalkData([], [], [])
    talk.title = title.split(':', 1)[-1]
    data.speaker_names.extend(speakers.split('and'))
    db.add_talk(talk, **data._asdict())


wayback = ''
url = wayback + 'https://wiki.python.org/moin/PyCon2006/Talks'
xpath = '//div[@id="content"]/*'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
header = find_first(entries, lambda e: e.tag == 'hr')
entries = entries[header+1:-1]
i = 0
counter = 0
print('talks')
print(url)
while i < len(entries):
    e = entries[i]
    # Empty dataset
    talk = Talk(category=Talk.TALK, conference_id=conference.id)
    data = db.TalkData([], [], [])
    # New title
    while i < len(entries) and ('cancelled' in e.text_content().lower() or 'entransit' in e.text_content().lower()):
        # Skip this talk
        print("skipping cancelled talk: {}".format(e.text_content()))
        try:
            i = i + 1 + find_first(entries[i+1:], lambda e: e.xpath('.//strong'))
        except StopIteration:
            i = len(entries)
            continue
        e = entries[i]
    talk.title = e.text_content().split('.', 1)[-1].strip()
    i += 1
    # Next up: speakers/organizations
    while i < len(entries) and not entries[i].tag == 'hr':
        e = entries[i]
        tmp = e.text_content().strip()
        if (
                not any(w in tmp.lower() for w in ('slides', 'lunch', 'agenda'))
                and (
                tmp.lower().endswith('inc.') or
                len(data.speaker_names) == 0 or (
                e.tag == 'p'
                and len(tmp) < 80
                and not re.search('[:.!?]$', tmp)
                and not '//' in tmp)
            )):
            tmp = tmp.split(':', 1)[-1]
            if '/' in tmp:  # Has a company name too
                if tmp.count('/') > 1:  # More than one
                    speakers, orgs = [z for z in zip(*[x.split('/') for x in tmp.split(',', 1)])]
                    data.speaker_names.extend(speakers)
                    data.organization_names.extend(orgs)
                else:
                    # Special case 'Vic / Kelson'
                    if tmp.startswith('Vic'):
                        data.speaker_names.append('Vic Kelson')
                    else:
                        speaker_name, org_name = tmp.split('/')
                        if '&' in speaker_name:
                            data.speaker_names.extend(speaker_name.split('&'))
                        else:
                            data.speaker_names.append(speaker_name)
                        data.organization_names.append(org_name)
            elif '&' in tmp:
                data.speaker_names.extend(tmp.split('&'))
            elif ',' in tmp:
                data.speaker_names.extend(tmp.split(','))
            else:
                if tmp.lower() != talk.title.lower() and len(tmp):
                    data.speaker_names.append(tmp)
        else: # The abstract
            if talk.abstract is None:
                talk.abstract = tmp
            else:
                talk.abstract = "\n".join((talk.abstract, tmp))
        i += 1
    i += 1
    counter += 1
    print("Finished talk. Counter = {}".format(counter))
    print(talk)
    print(data)
    db.add_talk(talk, **data._asdict())
    print("*" * 10)
