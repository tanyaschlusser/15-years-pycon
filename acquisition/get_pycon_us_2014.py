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
YEAR = 2014
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Montréal, QC',
        country = 'Canada',
        url = 'https://us.pycon.org/2014/',
        begin_date = datetime.date(YEAR, 4, 9),
        end_date = datetime.date(YEAR, 4, 17)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
url = 'https://us.pycon.org/2014/sponsors/'
response = requests.get(url)
root = html.fromstring(response.text)

## Sponsors
xpath = '//div[@class="sponsor"]//h4/text()'
for alt in root.xpath(xpath):
    if not alt.lower() == 'net-ng':
        sponsor_name = alt.rsplit('-', 1)[0].strip()
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()


## Volunteers
url = 'https://us.pycon.org/2014/about/staff/'
xpath = '//div[@class="box"]/*'
txt = html.fromstring(requests.get(url).text).xpath(xpath)[0].text_content()
print('volunteers')
print(url)
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
        print(new_name)

db.session.commit()


## Talks
## ~~~~~~
##
## Keynotes
keynotes = (
    (['John Perry Barlow'], 'Praising open communities and an open internet', ['Electronic Frontier Foundation'], 'http://pyvideo.org/pycon-us-2014/keynote-john-perry-barlow.html', ['community']),
    (['Fernando Pérez'], 'Python and science: how OSS and Python are transforming science', ['U.C. Berkeley'], 'http://pyvideo.org/pycon-us-2014/keynote-fernando-perez.html', ['ipython', 'notebook', 'science', 'history']),
    (['Jessica McKellar'], 'Python, the next generation', [], 'http://pyvideo.org/pycon-us-2014/.html', ['education', 'community']),
    (['Guido van Rossum'], 'Answering random Twitter questions', [], 'http://pyvideo.org/pycon-us-2014/keynote-guido-van-rossum-0.html', ['cpython'])
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
    xpath = '//div[contains(@class,"presentation")]/h3/a'
    entries = html.fromstring(requests.get(url).text).xpath(xpath)
    ## Iterate through and extract the relevant content
    for a in entries:
        title = a.text
        if 'canceled' in title.lower():
            continue
        root = html.fromstring(requests.get('https://us.pycon.org'+a.get('href')).text)
        speakers = root.xpath('//h4/a/text()')
        abstract = root.xpath('//div[@class="abstract"]')[0].text_content()
        try:
            level, topic = root.xpath('//dl/dd/text()')
        except ValueError:
            continue
        level = 'Beginner' if level == 'Novice' else level
        talk = Talk(category=category, conference_id=conference.id, title=title)
        data = db.TalkData(speakers, [topic], [])
        talk.abstract = abstract[:10000]
        talk.level = level
        db.add_talk(talk, **data._asdict())


url = 'https://us.pycon.org/2014/schedule/tutorials/list/'
add_presentation(url, Talk.TUTORIAL)

url = 'https://us.pycon.org/2014/schedule/talks/list/'
add_presentation(url, talk.TALK)

url = 'https://us.pycon.org/2014/schedule/posters/list/'
add_presentation(url, talk.POSTER)
