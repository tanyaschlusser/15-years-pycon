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
YEAR = 2010
wayback = 'https://web.archive.org/web/20100410015502/'
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Atlanta, GA',
        country = 'USA',
        url = wayback + 'http://us.pycon.org:80/2010/about/',
        begin_date = datetime.date(YEAR, 2, 17),
        end_date = datetime.date(YEAR, 2, 25)
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
    sponsor_name = alt.rsplit('-', 1)[0].strip()
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()


## Volunteers
wayback = 'https://web.archive.org/web/20100317190216/'
url = wayback + 'http://us.pycon.org:80/2010/about/staff/'
xpath = '//div[@id="content"]//tr/td[2]/text()'
print('volunteers')
print(url)
for volunteer_name in html.fromstring(requests.get(url).text).xpath(xpath):
    volunteer_name =  volunteer_name.strip('\n )') #volunteer_name.text_content().strip()
    if len(volunteer_name) == 0 or volunteer_name.startswith('('):
        continue
    # There can be multiple comma-separated names.
    for name in re.split("[,&/]", volunteer_name):
        new_name = " ".join(name.strip().split()[:2]).strip('( ')
        if new_name and len(new_name) > 1:
            if '.' in new_name:
                new_name = " ".join(name.strip().split()[:3])
            volunteer = db.fetch_or_add(Human(name=new_name))
            if conference not in volunteer.volunteering:
                volunteer.volunteering.append(conference)
    print(volunteer)

db.session.commit()


## Talks
wayback = 'https://web.archive.org/web/20100204143524/'
url = wayback + 'http://us.pycon.org/2010/conference/keynotes/'
keynotes = (
    (['Antonio Rodriguez'], 'Relentlessly Pursuing Opportunities With Python, or why the AIs will Spare Us All!'),
    (['Mark Shuttleworth'], 'Cadence, Quality, and Design')
)
for speaker_names, title in keynotes:
    talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
    talk.title = title
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
wayback = 'https://web.archive.org/web/20100213145202/'
url = wayback + 'http://us.pycon.org:80/2010/conference/talks/'
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
    if 'cancel' in talk.title.lower():
        continue
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
