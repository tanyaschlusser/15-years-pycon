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
YEAR = 2018
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Cleveland, OH',
        country = 'USA',
        url = 'https://us.pycon.org/2018/',
        begin_date = datetime.date(YEAR, 5, 9),
        end_date = datetime.date(YEAR, 5, 17)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
url = 'https://us.pycon.org/2018/sponsors/'
response = requests.get(url)
root = html.fromstring(response.text)

## Sponsors
xpath = '//div[@class="sponsor"]//a/img/@alt'
for alt in root.xpath(xpath):
    alt = alt[8:].strip()
    if not alt.lower() == 'net-ng':
        sponsor_name = alt.rsplit('-', 1)[0].strip()
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()


## Volunteers
url = 'https://us.pycon.org/2018/about/staff/'
xpath = '//div[@class="box-content"]'
print("visiting {}".format(url))
txt = html.fromstring(requests.get(url).text).xpath(xpath)[0].text_content()
for volunteer_name in re.findall('\*\*.+?\*\*', txt):
    volunteer_name =  volunteer_name.strip('*') #volunteer_name.text_content().strip()
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
    #(['Kelsey Hightower'], 'Kubernetes for Pythonistas', ['Google'], 'http://pyvideo.org/pycon-us-2017/keynote-kubernetes-for-pythonistas.html', ['voice', 'kubernetes', 'containers']),
)
for speaker_names, title, org, url, topics in keynotes:
    talk = Talk(category=Talk.KEYNOTE, conference_id=conference.id)
    talk.title = title
    talk.video_url = url
    data = db.TalkData(speaker_names, topics, org)
    db.add_talk(talk, **data._asdict())



## Tutorials, talks, and posters
def add_presentation(url, category):
    print("Collecting from {}".format(url))
    xpath = '//div[contains(@class,"box-content")]/*'
    entries = html.fromstring(requests.get(url).text).xpath(xpath)
    first = next(i for i,e in enumerate(entries) if e.tag == 'h2')
    ## Iterate through and extract the relevant content
    for i in range(int((len(entries)-first) / 3)):
        h2, p, div = entries[first + 3*i : first + 3*(1+i)]
        title = h2.text_content()
        if 'canceled' in title.lower():
            continue
        speakers = p.text_content().strip('\n ').split('\n', 1)[0].split(',')
        speakers = [s for s in speakers if s.strip() and not '?' in s]
        abstract = div.text_content().strip()
        talk = Talk(category=category, conference_id=conference.id, title=title)
        data = db.TalkData(speakers, [], [])
        talk.abstract = abstract[:10000]
        db.add_talk(talk, **data._asdict())


def add_presentation_from_table(url, category):
    print("Collecting from {}".format(url))
    xpath = '//td[contains(@class,"slot")]'
    entries = html.fromstring(requests.get(url).text).xpath(xpath)
    ## Iterate through and extract the relevant content
    for td in entries:
        a = td.find('./span[@class="title"]/a')
        if a is None:
            print('skipping...')
            continue
        title = a.text
        abstract = a.get('title')
        if 'canceled' not in title.lower():
            if 'Jasmine Hsu' in title:
                speakers = title.split(',')
                title = 'Fire, bullets, and productivity'
                level = 'Beginner'
            else:
                speakers =  td.findtext('./span[@class="speaker"]').strip()
                speakers = speakers.split(',') if ',' in speakers else speakers.split('&')
                speakers = [s for s in speakers if s.strip() and not '?' in s]
                level = td.xpath('./comment()')[0].text.splitlines()[1].strip()
                level = 'Beginner' if level == 'Novice' else level
            talk = Talk(category=category, conference_id=conference.id, title=title)
            data = db.TalkData(speakers, [], [])
            talk.abstract = abstract[:10000]
            talk.level = level
            db.add_talk(talk, **data._asdict())


    


url = 'https://us.pycon.org/2018/schedule/tutorials/'
add_presentation_from_table(url, Talk.TUTORIAL)

url = 'https://us.pycon.org/2018/schedule/sponsor-tutorials/'
add_presentation_from_table(url, Talk.TUTORIAL)


url = 'https://us.pycon.org/2018/schedule/talks/list/'
add_presentation(url, Talk.TALK)

url = 'https://us.pycon.org/2018/schedule/posters/list/'
add_presentation(url, Talk.POSTER)
