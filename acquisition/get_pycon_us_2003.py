import datetime
import difflib
import re
import requests
from lxml import html

from data import database as db
from data.database import Conference, Talk, Human, Organization, Topic


# helpers 
paren_url_matcher = re.compile("\(\s*ht\w*://[\w.-_~#]+\s*\)")
org_matcher = re.compile("(?<=\().+(?=\))")
separators = re.compile('[,|/;]')

def find_first(arr, match_fun):
    """`next(i for i,e in enumerate(arr) if match_fun(e))`"""
    return next(i for i,e in enumerate(arr) if match_fun(e))


# Add this conference
YEAR = 2003
wayback = 'https://web.archive.org/web/20021209003329/'
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Washington, DC',
        country = 'USA',
        url = wayback + 'http://python.org:80/pycon/',
        begin_date = datetime.date(YEAR, 3, 26),
        end_date = datetime.date(YEAR, 3, 28)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
# Hard code the sponsors, volunteers, and keynotes

## Sponsors
wayback = 'https://web.archive.org/web/20030802151012/'
url = wayback + 'http://www.python.org:80/pycon/dc2003/'
xpath = '//td[@class="body"]//p//img'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('sponsors')
print(url)
for e in entries:
    sponsor_name = e.get('alt')
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)
    print(sponsor)

other_sponsors = ("Artima.com", "MVM Studio", "New Riders", 
                  "Yet Another Society", "Addison Wesley", "Prentice Hall")
for sponsor_name in other_sponsors:
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)
    print(sponsor)

db.session.commit()


# Organizers
wayback = 'https://web.archive.org/web/20021209003329/'
url = wayback + 'http://python.org:80/pycon/'
xpath = '//td[@class="body"]/table/tr/td[1]/text()'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('organizers')
print(url)
for name in entries:
    volunteer = db.fetch_or_add(Human(name=name))
    if conference not in volunteer.volunteering:
        volunteer.volunteering.append(conference)
        print(volunteer)


## Talks
# - Keynotes
entries = (
    ('Python Features', 'Guido van Rossum', 'Zope Corporation'),
    ('The Hundred Year Language', 'Paul Graham', None)
)
for title, speaker, org in entries:
    talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
    data = db.TalkData([], [], [])
    talk.title = title
    data.speaker_names.append(speaker)
    if org is not None:
        data.organization_names.append(org)
    db.add_talk(talk, **data._asdict())

# - Tutorials
# None? -- False; there are some intermixed with the talks;
#          search for 'tutorial' in the title/abstract

# - Regular talks
url = 'https://wiki.python.org/moin/PyConDC2003/Speakers'
xpath = '//div[@id="content"]/*[not(self::span)]'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
header = next(i for i,e in enumerate(entries) if e.tag == 'h2')
entries = entries[header:]
names_splitter = re.compile('(,(?! Jr)| and | &)+')
talk = Talk(category=Talk.TALK, conference_id=conference.id)
data = db.TalkData([], [], [])
print('regular talks')
print(url)
for e in entries:
    text = e.text_content().strip()
    if e.tag == 'h2':
        # Possibly finished
        if talk.title is not None:
            if ('tutorial' in talk.title.lower() or
                    (talk.abstract is not None 
                    and 'tutorial' in talk.abstract.lower())):
                talk.category = Talk.TUTORIAL
            db.add_talk(talk, **data._asdict())
            print(talk)
            print(data)
            print("*" * 10)
            talk = Talk(category=Talk.TALK, conference_id=conference.id)
            data = db.TalkData([], [], [])
        names = e.text_content()
        if '&' in names or ' and ' in names or ',' in names:
            names = names_splitter.sub('|', e.text_content()).split('|')
            data.speaker_names.extend(names)
        else:
            data.speaker_names.append(names)
    else:
        title = e.findtext('./strong')
        if title is None:
            # abstract
            if talk.abstract is None:
                talk.abstract = e.text_content()
            else:
                talk.abstract = '\n'.join((talk.abstract, e.text_content()))
        else:
            talk.title = title

# don't forget last one
if talk.title is not None:
    if ('tutorial' in talk.title.lower() or
            (talk.abstract is not None 
            and 'tutorial' in talk.abstract.lower())):
        talk.category = Talk.TUTORIAL
    db.add_talk(talk, **data._asdict())
    print(talk)
    print(data)
    print("*" * 10)
