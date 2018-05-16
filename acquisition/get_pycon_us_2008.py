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
YEAR = 2008
wayback = 'https://web.archive.org/web/20080906013119/'
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Chicago, IL',
        country = 'USA',
        url = wayback + 'http://us.pycon.org/2008/about/',
        begin_date = datetime.date(YEAR, 3, 13),
        end_date = datetime.date(YEAR, 3, 30)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
# Get the conference details from the Wayback machine
response = requests.get(conference.url)
root = html.fromstring(response.text)

## Sponsors
xpath = '//div[@id="sponsors"]//li//img/@alt'
for alt in root.xpath(xpath):
    sponsor_name = alt.split('-')[0].strip()
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()

## Volunteers
wayback = 'https://web.archive.org/web/20080517032419/'
url = wayback + 'http://us.pycon.org/2008/about/staff'
xpath = '//div[@id="content"]//tr/td[2]/text()'
print('volunteers')
print('url')
for volunteer_name in html.fromstring(requests.get(url).text).xpath(xpath):
    volunteer_name =  volunteer_name.strip() #volunteer_name.text_content().strip()
    if len(volunteer_name) == 0:
        continue
    # There can be multiple comma-separated names.
    for name in re.split("[,&]", volunteer_name):
        name = " ".join(name.strip().split()[:2])
        volunteer = db.fetch_or_add(Human(name=name))
        if conference not in volunteer.volunteering:
            volunteer.volunteering.append(conference)

db.session.commit()


## Talks
wayback = 'https://web.archive.org/web/20080907065646/'
url = wayback + 'http://us.pycon.org/2008/conference/keynotes/'
xpath = '//div[@id="keynote-talks"]/div[@class="section"]'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('talks')
print(url)
for e in entries:
    talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
    data = db.TalkData([], [], [])
    data.speaker_names.append(e.findtext('h1'))
    # Split off the abstract, and remove the 'Topic:' prefix
    tmp = e.xpath('*[text()[contains(.,"Topic")]]')
    if len(tmp) == 0:
        talk.title = "Keynote"
    else:
        tmp =  re.split('[(:]', tmp[0].text_content()[7:].strip(')'))
        talk.title = tmp[0].strip()
        talk.abstract = ' '.join(tt for t in tmp[1:] for tt in t.split('\n'))
    db.add_talk(talk, **data._asdict())


# Tutorials
wayback = 'https://web.archive.org/web/20090202113211/'
url = wayback + 'http://us.pycon.org:80/2008/tutorials/schedule/'
xpath = '//div[@id="content"]//li'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
# Iterate through and extract the relevant content
print('tutorials')
print(url)
for e in entries:
    tmp = e.text_content()
    if 'cancel' in tmp.lower():
        continue
    else:
        tmp = tmp.split(' [', 1)[0]
        title, speakers = tmp.strip(') ').rsplit('(', 1)
        data = db.TalkData([], [], [])
        talk = Talk(category=Talk.TUTORIAL, conference_id=conference.id)
        talk.title = title
        speakers = ', '.join(speakers.split(' and '))
        data.speaker_names.extend(s for s in speakers.split(',') if len(s))
        db.add_talk(talk, **data._asdict())


duration = re.compile('\d+min ')
wayback = 'https://web.archive.org/web/20081204100015/'
url = wayback + 'http://us.pycon.org:80/2008/conference/talks/'
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
    talk.level = duration.sub('', txt).lower()
    # keywords
    i += 1
    txt = rows[i].text_content().strip()
    data.topic_names.extend(txt.split(','))
    # abstract
    i += 1
    talk.abstract = rows[i].text_content().strip()
    db.add_talk(talk, **data._asdict())
    print(talk)
    print(data)
