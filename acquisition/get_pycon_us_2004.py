import datetime  # TANYA: 51 talks 0 abstracts
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
YEAR = 2004
wayback = ''
conference = Conference(
        name = 'pycon-us',
        year = YEAR,
        location = 'Washington, DC',
        country = 'USA',
        url = wayback + 'https://wiki.python.org/moin/PyConDC2004',
        begin_date = datetime.date(YEAR, 3, 20),
        end_date = datetime.date(YEAR, 3, 26)
)

conference = db.fetch_or_add(conference)
db.session.commit()


## ----------------------------------------------------------------------------
# Hard code the sponsors, volunteers, and keynotes

## Sponsors
wayback = 'https://web.archive.org/web/20050211030102/'
url = wayback + 'http://www.python.org:80/pycon/dc2004/'
xpath = '//td[@class="body"]//p//img'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('sponsors')
print(url)
for e in entries:
    sponsor_name = e.get('alt')
    sponsor = db.fetch_or_add(Organization(name=sponsor_name))
    sponsor.sponsorships.append(conference)

db.session.commit()


## Volunteers
# Session chairs
url = 'https://wiki.python.org/moin/PyConDC2004/SessionChairs'
xpath = '//div[@id="content"]/p'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('volunteers')
print(url)
for e in entries:
    txt = e.text_content()
    if '--' in txt:
        name = txt.rsplit('--', 1)[-1].strip()
        if not name == 'UNCLAIMED':
            print('volunteer: {}'.format(name))
            volunteer = db.fetch_or_add(Human(name=name))
            if conference not in volunteer.volunteering:
                volunteer.volunteering.append(conference)

db.session.commit()

# Organizers
url = 'http://ftp.ntua.gr/mirror/python/pycon/dc2004/committee.html'
xpath = '//td[@class="body"]/table/tr/td[1]/text()'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('organizers')
print(url)
for name in entries:
    volunteer = db.fetch_or_add(Human(name=name))
    if conference not in volunteer.volunteering:
        volunteer.volunteering.append(conference)


## Talks
# - Keynotes
entries = (
    ('The virtues of Open Source', 'Mitch Kapor', 'Open Source Applications Foundation (OSAF)'),
    ('Python State of the Union', 'Guido van Rossum', 'Zope corporation'),
    ('How to argue about typing', 'Bruce Eckel', None)
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
# None? -- True. (PostMortem recommends tutorials for 2005)

# - Regular talks
#wayback = 'https://web.archive.org/web/20050206212138/'
#url = wayback + 'http://www.python.org:80/pycon/dc2004/schedule.html
url = 'https://wiki.python.org/moin/PyConDC2004/TalksByCategory'
#xpath = '//td[@class="body"]/table/tbody/tr'
xpath = '//div[@id="content"]/*'
entries = html.fromstring(requests.get(url).text).xpath(xpath)
header = next(i for i,e in enumerate(entries) if e.tag == 'h1')
entries = entries[header:]
speaker_lookup = {}
topic = None
talk = Talk(category=Talk.TALK, conference_id=conference.id)
data = db.TalkData([], [], [])
for e in entries:
    text = e.text_content()
    if e.tag == 'h1':
        topic = text
        talk = Talk(category=Talk.TALK, conference_id=conference.id)
        data = db.TalkData([], [topic], [])
    else:
        if '--' in text:
            title, speaker = text.split(' -- ')
        elif 'Kuchling' in text:  # A.M. Kuchling
            title, speaker = text.split('A.M. ')
            speaker, org = speaker.strip().rsplit(' ', 1)
            speaker = 'A.M. ' + speaker
            data.organization_names.append(org)
        else:
            continue
        if ',' in speaker:
            speaker, org = speaker.split(',', 1)
            data.organization_names.append(org)
        talk.title = title
        data.speaker_names.extend(speaker.split(' and '))
        print(talk)
        print(data)
        for speaker_name in data.speaker_names:
            if speaker_name not in speaker_lookup:
                speaker_lookup[speaker_name] = [(talk, data)]
            else:
                speaker_lookup[speaker_name].append((talk, data))
        print("*" * 10)




def add_new_talk(title, abstract, speaker, topic):
    if abstract and "__wbhack.init('https://web.archive.org/web');" in abstract:
        abstract = abstract.split("__wbhack.init('https://web.archive.org/web');", 1)[-1]
    db.add_talk(
        Talk(category=Talk.TALK, conference_id=conference.id, title=title, abstract=abstract),
        **db.TalkData([speaker], [topic], [])._asdict())
    print("adding new one not in list:", speaker, title, "\n***\n")


# Add the paper texts.
# The prior lookup should have gotten people, topics, and title.
wayback = 'https://web.archive.org/web/20050206204550/'
url = wayback + 'http://www.python.org:80/pycon/dc2004/papers/'
xpath = '//td[@class="body"]/table/tr'
topics = []
entries = html.fromstring(requests.get(url).text).xpath(xpath)
print('papers')
print(url)
for row in entries:
    cols = row.xpath('./td')
    if len(cols) != 3:
        continue
    elif cols[1].get('bgcolor') == '#003366':
        # It's a topic -- strip the I, II, III suffixes
        topics = [c.text_content().strip().rstrip('I ') for c in cols[1:]]
    else:
        # Actual talks
        titles_speakers = [
                tuple(c.text_content().strip().rsplit('\n', 1))
                for c in cols[1:]]
        links = [url + c.find('./a').get('href') if c.find('./a') is not None else None for c in cols[1:]]
        abstracts = [
                html.fromstring(requests.get(lnk).text.encode('utf-8')).text_content() if lnk else None
                for lnk in links]
        for i in (0, 1):
            print(titles_speakers)
            title, speaker_name = titles_speakers[i]
            abstract = abstracts[i]
            topic = topics[i]
            # Try to use existing talk/data
            found_speaker = difflib.get_close_matches(speaker_name, speaker_lookup.keys(), 1)
            if found_speaker:
                speaker = found_speaker[0]
                # Get the correct talk if there are multiple
                if len(speaker_lookup[speaker]) == 0:
                    add_new_talk(title, abstract, speaker, topic)
                    continue
                elif len(speaker_lookup[speaker]) == 1:
                    i = 0
                else:
                    title_list = [t.title for t,d in speaker_lookup[speaker]]
                    # Error if not find anything -- so I'll know whether this method is bad
                    try:
                        best_title = difflib.get_close_matches(title, title_list, 1)[0]
                        i = next(i for i,t in enumerate(title_list) if t==best_title)
                    except IndexError:
                        add_new_talk(title, abstract, speaker, topic)
                        continue
                talk, data = speaker_lookup[speaker].pop(i)
                if len(speaker_lookup[speaker]) == 0:
                    del speaker_lookup[speaker]
                talk.abstract = abstract
                data.topic_names.append(topic)
                db.add_talk(talk, **data._asdict())
                print(talk)
                print(data)
                print("*" * 10)
            else:
                db.add_talk(
                    Talk(category=Talk.TALK, conference_id=conference.id, title=title, abstract=abstract),
                    **db.TalkData([speaker_name], [topic], [])._asdict())
                print("adding new one not in list:", speaker_name, title, "\n***\n")


# Add all the remaining talks that haven't been added yet.
talk_lookup = {}
for talk, data in [td for v in speaker_lookup.values() for td in v]:
    talk_lookup[talk] = data

for talk, data in talk_lookup.items():
    db.add_talk(talk, **data._asdict())
    print(talk)
    print(data)
    print("*" * 10)
