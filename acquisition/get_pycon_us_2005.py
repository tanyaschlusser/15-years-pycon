import datetime
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
YEAR = 2005
wayback = ''
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Washington, DC',
        country = 'USA',
        url = wayback + 'https://wiki.python.org/moin/PyConDC2005',
        begin_date = datetime.date(YEAR, 3, 19),
        end_date = datetime.date(YEAR, 3, 25)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
# Hard code the sponsors, volunteers, and keynotes

## Sponsors
# Copied by hand from:
# ftp://ftp.ntua.gr/mirror/python/pycon/2005/index.html
sponsor_names = (
    'White Oak Technologies, Inc.',
    'ActiveState',
    'OSAF',
    'Google',
    'Hostway',
    'Interlix',
    'Openhosting',
    'Secure Software',
    'Tummy.com',
    'Wingware',
    'Zettai')
for sponsor_name in sponsor_names:
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()


## Volunteers
# The editors of the wiki (wiki-->info)
# plus section managers (https://wiki.python.org/moin/PyConDC2005)
volunteer_names = (
    'Steve Holden',
    'Ian Bicking',
    'Andrew Kuchling',
    'Stephan Deibel',
    'Jim Fulton',
    'Jeremy Hylton'
)
for name in volunteer_names:
    volunteer = db.fetch_or_add(Human(name=name))
    if conference not in volunteer.volunteering:
        volunteer.volunteering.append(conference)

db.session.commit()

## Talks
# - Keynotes
entries = (
    ('Python on the .NET Platform', 'Jim Hugunin', 'Microsoft Corporation'),
    ('The State of Python', 'Guido van Rossum', 'Elemental Security'),
    ('What is the PSF?', 'PSF Board', 'Python Software Foundation'),
    ('Python at Google', 'Greg Stein', 'Google')
)
for title, speaker, org in entries:
    talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
    data = db.TalkData([], [], [])
    talk.title = title
    data.speaker_names.append(speaker)
    data.organization_names.append(org)
    db.add_talk(talk, **data._asdict())

# - Tutorials
# None?

# - Regular talks
url = 'https://wiki.python.org/moin/PyConDC2005/Presentations/'
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
        tmp = paren_url_matcher.sub('', e.text_content().strip().strip(','))
        if len(data.speaker_names) == 0:
            #tmp = tmp.split(':', 1)[-1]
            if '/' in tmp:  # Has a company name too
                if tmp.count('/') > 1:  # More than one
                    print("!" * 90)
                    print("Multiple slashes:")
                    print(tmp)
                else:
                    # Special case 'Vic / Kelson'
                    if tmp.startswith('Vic'):
                        data.speaker_names.append('Vic Kelson')
                    else:
                        speaker_name, org_name = tmp.split('/')
                        if 'and' in speaker_name:
                            data.speaker_names.extend(speaker_name.split(' and '))
                            data.organization_names.extend(org_name.split(' and '))
                        elif ',' in speaker_name:
                            # Require 2 words after comma
                            comma = speaker_name.find(',')
                            if comma > -1 and len(re.findall('\w+', speaker_name[comma:])) > 1:
                                data.speaker_names.extend(speaker_name.split(','))
                            else:
                                data.speaker_names.append(speaker_name)
                        else:
                            data.speaker_names.append(speaker_name)
                            if 'M.E Computer Science' in org_name:
                                data.organization_names.append(re.sub('M.E Computer Science,', '', org_name))
                            else:
                                data.organization_names.append(org_name)
            elif '&' in tmp:
                data.speaker_names.extend(tmp.split('&'))
            elif ',' in tmp:
                # Require 2 words after comma
                comma = tmp.find(',')
                if comma > -1 and len(re.findall('\w+', tmp[comma:])) > 1:
                    data.speaker_names.extend(tmp.split(','))
                else:
                    data.speaker_names.append(tmp)
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
