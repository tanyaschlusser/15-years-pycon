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
YEAR = 2009
wayback = 'https://web.archive.org/web/20090531044807/'
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Chicago, IL',
        country = 'USA',
        url = wayback + 'http://us.pycon.org/2009/about/',
        begin_date = datetime.date(YEAR, 3, 25),
        end_date = datetime.date(YEAR, 4, 2)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
# Get the conference details from the Wayback machine
response = requests.get(conference.url)
root = html.fromstring(response.text)

## Sponsors
xpath = '//div[@id="spx123"]//li//img/@alt'
for alt in root.xpath(xpath):
    sponsor_name = alt.split('-')[0].strip()
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()

## Volunteers
wayback = 'https://web.archive.org/web/20090409180624/'
url = wayback + 'http://us.pycon.org:80/2009/about/staff/'
xpath = '//div[@id="content"]//tr/td[2]/text()'
print('volunteers')
print(url)
for volunteer_name in html.fromstring(requests.get(url).text).xpath(xpath):
    volunteer_name =  volunteer_name.strip('\n )') #volunteer_name.text_content().strip()
    if len(volunteer_name) == 0:
        continue
    # There can be multiple comma-separated names.
    for name in re.split("[,&]", volunteer_name):
        name = " ".join(name.strip().split()[:2])
        if name and len(name) > 1:
            volunteer = db.fetch_or_add(Human(name=name))
            if conference not in volunteer.volunteering:
                volunteer.volunteering.append(conference)

db.session.commit()


## Talks
keynotes = (
    (['Guido van Rossum'], 'Update on the state of Python', None),
    (['Steve Huffman', 'Alexis Ohanian'], 'Reddit', "Reddit's origin and the switch to Python")
)
for speaker_names, title, abstract in keynotes:
    talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
    talk.title = title
    if title == 'Reddit':
        data.organization_names.append('Reddit')
    if abstract:
        talk.abstract = abstract
    data = db.TalkData(speaker_names, [], [])
    db.add_talk(talk, **data._asdict())
    

## Tutorials
##  ==> Ignore these...the links are broken and only the presenters'
##      last names are given, so it is hard to create an entry.
##
#wayback = 'https://web.archive.org/web/20090518174359/'
#url = wayback + 'http://us.pycon.org:80/2009/tutorials/schedule'
#xpath = '//div[@id="tutorials"]//li'
#entries = html.fromstring(requests.get(url).text).xpath(xpath)
## Iterate through and extract the relevant content
#for e in entries:
#    tmp = e.text_content()
#    if 'cancel' in tmp.lower():
#        continue
#    else:
#        tmp = tmp.split(' [', 1)[0]
#        title, speakers = tmp.strip(') ').rsplit('(', 1)
#        data = db.TalkData([], [], [])
#        talk = Talk(category=Talk.TUTORIAL, conference_id=conference.id)
#        talk.title = title
#        speakers = ', '.join(speakers.split(' and '))
#        data.speaker_names.extend(s for s in speakers.split(',') if len(s))
#        db.add_talk(talk, **data._asdict())


duration = re.compile('\d+min ')
wayback = 'https://web.archive.org/web/20090314014205/'
url = wayback + 'http://us.pycon.org:80/2009/conference/talks/'
#xpath = '//div[@class="proposal-list-summary"]/*'
xpath = '//*[contains(@class, "proposal_list_summary")]'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('talks')
print(url)
for e in entries:
    rows = e.xpath('./*[self::h2 or self::span or self::div]')
    talk = Talk(category=Talk.TALK, conference_id=conference.id)
    data = db.TalkData([], [], [])
    talk.title = rows[0].text_content().split('\n')[1].strip()
    i = 1  # skip talk number (i=0)
    while i < len(rows):
        # people
        txt = rows[i].text_content().strip(';')
        if duration.match(txt):
            break
        else:
            data.speaker_names.append(txt.split('(')[0].split(' bio')[0])
            data.organization_names.extend(re.findall('(?<=\()[^\)]+(?=\))',txt))
            i += 1
    talk.level = txt.strip().split()[-1].lower()
    # keywords
    i += 2
    txt = rows[i].text_content().strip()
    data.topic_names.extend(txt.split(','))
    # abstract
    i += 1
    talk.abstract = rows[i].text_content().strip()
    db.add_talk(talk, **data._asdict())
