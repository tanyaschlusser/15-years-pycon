# -*- coding: utf-8 -*-
# These functions read from the data directory inside this folder
import codecs
import csv
import datetime
import json
import os

from collections import namedtuple

Release = namedtuple('Release', ['rel', 'dt', 'url', 'peps'])
XY = namedtuple('XY', ['x', 'y'])

def get_json(fname):
    return json.loads(open(os.path.join('data', fname)).read())


def to_xy(row):
     country, abbr, city, xy = row.split('|') 
     x, y = (float(f) for f in xy.split(','))
     return city, XY(x, y)


def ingest_keynotes(fname):
    keynotes = {}
    yr = None
    for row in open(os.path.join('data', fname)):
        if row.strip():
            if not row.startswith(' '):
                yr = int(row[:4])
                keynotes[yr] = row[7:].strip()
            else:
                keynotes[yr] += ' ' + row[7:].strip()
    return keynotes
    

def ingest_conferences(fname):
    xys = dict(to_xy(row) for row in open(os.path.join('data', 'cities_xy.txt')).read().splitlines())
    entries = open(os.path.join('data', fname)).read().splitlines()
    row = entries.pop(0)
    indices = [0] + [i+1 for i in range(1,len(row)) if row[i]==' ' and row[i+1]!=' ']
    indices = zip(indices,indices[1:])
    cols = [row[i:j].strip() for i,j in indices]
    intermediate = [
        dict(zip(cols, [row[i:j].strip() for i,j in indices]))
        for row in entries]
    result = dict()
    for yr in cols:
        if yr[0] != '2' or yr == '2002':
            continue
        result[yr] = []
        for row in intermediate:
            city = row[yr]
            conference = row['Con'].split('(', 1)[-1].strip(')')
            if len(city) and city != '-' and city[0] != '(':
                for c in city.split('+'):
                    result[yr].append((conference, xys[c]))
    return result


def to_date(datestring):
    return datetime.date(*[int(i) for i in datestring.split('-')])

def to_rows(csvrow):
    rel, dt, url, peps = csvrow
    return Release(rel, to_date(dt), url, list(p if p != 'x' else '' for p in peps.split('|') if len(p)))


graph = get_json('topic_graph_byhand.json')
#pep_descs = get_json('pep_descs.json')
sorted_cats = get_json('sorted_cats.json')
topic_order = get_json('topic_order.json')
citations = codecs.open(os.path.join('data', 'citations.txt'), encoding='utf-8').read().splitlines()
citations = u'~   {}   ~'.format(u'   ~   '.join(citations))

#rel_to_peps = map(to_rows, csv.reader(open(os.path.join('data', 'detailed_rel_to_peps.txt'))))
pycon_dates = json.loads(open(os.path.join('data', 'pycon_dates.json')).read())
for row in pycon_dates:
    row['begin_date'] = to_date(row['begin_date'])
    row['end_date'] = to_date(row['end_date'])
world_conferences = ingest_conferences('conferences.txt')
keynotes = ingest_keynotes('keynotes.txt')

def history_rows(row):
    dt, event, category = row.split('|')
    return to_date(dt), event, category

history = [history_rows(row) for row in open(os.path.join('data', 'history.txt')).read().splitlines()]
notes = '\n\n'.join(' '.join(s.splitlines()) for s in open(os.path.join('data', 'notes.txt')).read().split('\n\n'))
