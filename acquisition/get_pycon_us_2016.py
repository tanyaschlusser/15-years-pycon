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
YEAR = 2016
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Portland, OR',
        country = 'USA',
        url = 'https://us.pycon.org/2016/',
        begin_date = datetime.date(YEAR, 5, 28),
        end_date = datetime.date(YEAR, 6, 5)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
url = 'https://us.pycon.org/2016/sponsors/'
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
url = 'https://us.pycon.org/2016/about/staff/'
xpath = '//div[@class="box"]/*'
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
    (['Cris Ewing'], 'Adaptation in OSS', ['Plone'], 'http://pyvideo.org/pycon-us-2016/cris-ewing-keynote-pycon-2016.html', ['Plone', 'CMS', 'growth', 'change']),
    (['Lorena Barba'], 'Beyond learning to program: education, open source culture, and structured collaboration in language.', ['George Washington University', 'NumFocus'], 'http://pyvideo.org/pycon-us-2016/lorena-barba-keynote-pycon-2016.html', ['education', 'OSS', 'community', 'language']),
    (['Parisa Tabriz'], 'The hacker spectrum: tales of people that break software and why being hacker-friendly can lead to better software security', ['Google'], 'http://pyvideo.org/pycon-us-2016/parisa-tabriz-keynote-pycon-2016.html', ['security', 'hacker']),
    (['K Lars Lohn'], 'Complexity and the art of the Left Turn', [], 'http://pyvideo.org/pycon-us-2016/.html', ['culture', 'community', 'language']),
    (['Guido van Rossum'], 'Mini state of Python, plus why Python is successful', ['Dropbox'], 'http://pyvideo.org/pycon-us-2016/guido-van-rossum-python-language-pycon-2016.html', ['Python 3', 'community', 'durability', 'feedback'])
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
            level = root.xpath('//dl/dd/text()')[0]
        except ValueError:
            continue
        level = 'Beginner' if level == 'Novice' else level
        talk = Talk(category=category, conference_id=conference.id, title=title)
        data = db.TalkData(speakers, [], [])
        talk.abstract = abstract[:10000]
        talk.level = level
        db.add_talk(talk, **data._asdict())


def add_presentation_from_table(url, category):
    print("Collecting from {}".format(url))
    xpath = '//td[contains(@class,"slot")]'
    entries = html.fromstring(requests.get(url).text).xpath(xpath)
    ## Iterate through and extract the relevant content
    for td in entries:
        a = td.find('./span[@class="title"]/a')
        if a is None:
            continue
        title = a.text
        abstract = a.get('title')
        if 'canceled' not in title.lower():
            speakers =  td.findtext('./span[@class="speaker"]').strip()
            speakers = speakers.split(',') if ',' in speakers else speakers.split('&')
            level = td.findtext('./span[@class="audience_level"]').strip()
            level = 'Beginner' if level == 'Novice' else level
            talk = Talk(category=category, conference_id=conference.id, title=title)
            data = db.TalkData(speakers, [], [])
            talk.abstract = abstract[:10000]
            talk.level = level
            db.add_talk(talk, **data._asdict())

    


url = 'https://us.pycon.org/2016/schedule/tutorials/'
add_presentation_from_table(url, Talk.TUTORIAL)

url = 'https://us.pycon.org/2016/schedule/sponsor-tutorials/'
add_presentation_from_table(url, Talk.TUTORIAL)

url = 'https://us.pycon.org/2016/schedule/talks/'
add_presentation_from_table(url, talk.TALK)

url = 'https://us.pycon.org/2016/schedule/posters/list/'
add_presentation(url, talk.POSTER)
