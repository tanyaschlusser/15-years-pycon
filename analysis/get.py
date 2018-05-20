"""
Helper library to get the data, etc
"""
import inspect
import json
import os
import sys 
import nltk

# Add this project to the path so we can access the database
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
from data import database as db
from data.database import Conference, Talk


stemmer = nltk.stem.snowball.SnowballStemmer('english')
stopwords = nltk.corpus.stopwords.words('english')
# These were added after the first couple of iterations because they
# add no insight about their topic but are common in the abstracts.
stopwords.extend([
    'also', 'code', 'develop', 'http',
    'know', 'learn',
    'paper', 'presentation', 'python',
    'should',
    'talk', 'tool',
    'understand', 'use', 'uses', 'used', 'want', 'work', 'would'
])

def bigrams(text, stem=True):
    stem = stemmer.stem if stem else lambda x: x
    tuples = nltk.bigrams(
        stem(s) for s in nltk.word_tokenize(text)
        if len(s) > 1 and not s in stopwords
    )
    return (' '.join(t) for t in tuples)

def unigrams(text, stem=True):
    stem = stemmer.stem if stem else lambda x: x
    return (
        stem(s) for s in nltk.word_tokenize(text) if len(s) > 1
        and not s in stopwords
    )

def nouns(text):
    tokens = nltk.word_tokenize(text.lower())
    nouns = [
        (tag,word) for word, tag in nltk.pos_tag(tokens)
            if tag.startswith('NN')
                and not word.lower() in stopwords and '/' not in word
    ]
    return set([word for tag, word in nouns])


def nouns_and_verbs(text):
    tokens = nltk.word_tokenize(text.lower())
    nouns_and_verbs = [
        (tag,word) for word, tag in nltk.pos_tag(tokens)
            if (tag.startswith('NN') or tag.startswith('V'))
                and not word.lower() in stopwords and '/' not in word
    ]
    return set([word for tag, word in nouns_and_verbs])


def talks(year=None):
    q = db.session.query(Talk).filter_by(category=Talk.TALK)
    if year is not None and isinstance(year, int):
        q = q.filter(Conference.year==year)
    for talk in q.distinct().all():
        yield talk

def talk_counts(year=None):
    q = db.session.query(Talk, Conference).filter_by(category=Talk.TALK)
    if year is not None and isinstance(year, int):
        q = q.filter(Conference.id==Talk.conference_id)
        q = q.filter(Conference.year==year)
    return q.count()


# ~~~~~ Categorizations
def categories():
    return json.load(open('categories.json'))


def categories_fixed(d):
    for topic in d.keys():
        words = d[topic]
        if topic in fixed_cats:
            for word in words:
                if word in fixed_cats[topic]:
                    replacement_word = fixed_cats[topic][word]
                    d[topic][replacement_word] = d[topic][word]
                    del d[topic][word]
            if 'FUNCTIONS' in fixed_cats[topic]:
                for fun in fixed_cats[topic]['FUNCTIONS']:
                    fun(d[topic])



def replace_in(d, keep_key, replace_keys, fun=(lambda v1, v2: v1 + v2), init=0):
    if keep_key not in d:
        d[keep_key] = init
    for k in replace_keys:
        if k in d:
            d[keep_key] = fun(d[keep_key], d[k])
            del d[k]
    if d[keep_key] == 0:
        del d[keep_key]


def subtract_from(d, key, subtract_keys, fun=(lambda v1, v2: v1 - v2)):
    if key in d:
        for k in subtract_keys:
            if k in d:
                d[key] = fun(d[key], d[k])
        if d[key] == 0:
            del d[key]



fixed_cats = {
    'education': {'educat':'education'},
    'collaboration': {
        'collab':'collaboration', 'maintainab':'maintainability',
        'problem solv':'problem solving'
    },
    'documentation': {'FUNCTIONS':[(lambda d: subtract_from(d, 'docs', ('docstring',)))]},
    'cloud': {'rackspace':'Rackspace', 'heroku':'Heroku'},
    #'microlanguage': {' dsl':'DSL'},
    #'science': {'anaconda':'Anaconda', 'enthought':'Enthought', 'ipython':'iPython', 'jupyter':'Jupyter'},
    'acquisition': {'requests library':'Requests', 'FUNCTIONS': [(lambda d: replace_in(d, 'scraping', ('scrape', )))]},
    'neural net': {'keras':'Keras'},
    'text': {'nltk':'NLTK', 'FUNCTIONS': [(lambda d: replace_in(d, 'text mining', ('text min', 'text ana')))]},
    'GIS': {' gis':'GIS'},
    'machine learning': {
        'data scie': 'data science', 'data min': 'data mining', 'statist': 'statistics',
        'sentiment': 'sentiment analysis', 'kaggle': 'Kaggle', 'opencv':'OpenCV',
        'FUNCTIONS': [
            (lambda d: replace_in(d, 'data frame', ('dataframe', ))),
            (lambda d: replace_in(d, 'sklearn', ('scikit',))),
            (lambda d: replace_in(d, 'time series', ('time-series',)))
        ]
    },
    'IPython/Jupyter': {'ipython':'IPython', 'jupyter':'Jupyter'},
    'visualization': {
        'visual': 'visualization',
        'FUNCTIONS': [
            (lambda d: subtract_from(d, 'plot', ('plotly', 'plot.ly'))),
            (lambda d: replace_in(d, 'plot.ly', ('plotly',)))
        ]
    },
    'image': {' pil':'PIL', 'opengl':'OpenGL', 'gimp':'GIMP'},
    'application': {
        'gtk':'GTK', 'tkinter':'TkInter', 'qt':'Qt', 'wxpython':'wxPython',
        ' ship':'ship', 'sdk':'SDK', 'user inter':'user interface'
    },
    'database': {
        'postgres':'postgreSQL', ' sql':'sql', 'mvc':'MVC',
        'zodb':'ZODB', 'django orm':'Django ORM', 'pony orm':'pony ORM',
        'sqlalchemy':'sqlAlchemy', 'sqlobject': 'sqlObject',
        'FUNCTIONS': [
            (lambda d: replace_in(d, 'uptime', ('up time',))),
            (lambda d: replace_in(d, 'MVC/MVT', ('mvc', 'mvt'))),
            (lambda d: subtract_from(d, 'sql', ('sqlAlchemy', 'sqlite3', 'sqlObject'))),
            (lambda d: subtract_from(d, 'relational database', ('rdbms', ))),
            (lambda d: subtract_from(d, 'data storage', ('datastore', 'data stor')))
        ]
    },
    'NOSQL': {
        'cassandra':'Cassandra', 'couch':'Couch', 'hadoop':'Hadoop',
        'hdfs':'HDFS', 'mongo':'MongoDB', 'nosql':'noSQL', 'memcach':'Memcached',
        'redis':'Redis', 'spark':'Spark', 'impala':'Impala', 'yarn':'Yarn',
        'mapreduce':'MapReduce', 'storm':'Storm'
    },
    'web': {
        ' rpc':'RPC', ' cms':'CMS', 'django':'Django', 'flask':'Flask',
        'genshi':'Genshi', 'jinja':'Jinja', 'pyramid':'Pyramid',
        'pylons':'Pylons', 'bottle ':'bottle', 'turbogears':'TurboGears',
        'wsgi':'WSGI', 'zope':'Zope', 'gunicorn':'Gunicorn',
        'FUNCTIONS': [
            (lambda d: replace_in(d, 'web development', ('web app', 'web framework', 'web site', 'web develop')))
        ]
    },
    'continuous deployment': {'ansible':'Ansible', 'chef':'Chef', 'fabric':'Fabric', 'puppet':'Puppet'},
    'scaling data pipeline':  {'celery':'Celery', 'zeromq':'ZeroMQ', 'rabbitmq':'RabbitMQ', 'kafka':'Kafka', 'smtp':'SMTP'},
    'scaling web traffic': {
        'load balanc':'load balancing', 'supervisor':'Supervisor',
        'FUNCTIONS': [
            (lambda d: replace_in(d, 'scaling', ('scalab', ))),
            (lambda d: replace_in(d, 'real-time', ('realtime', )))
        ]
    },
    'monitoring': {'logg':'logging', 'splunk':'Splunk', 'diagnostic':'diagnostics', 'monitor':'monitoring'},
    'devops': {
        'jenkins':'Jenkins', 'travis':'Travis CI', 'docker':'Docker', 'kubernetes':'Kubernetes',
        'FUNCTIONS': [
            (lambda d: replace_in(d, 'DevOps', ('devops', 'dev/ops', 'dev-ops',  'operations', ' ops'))),
            (lambda d: replace_in(d, 'automation', ('automate',))),
            (lambda d: replace_in(d, 'microservice', ('micro-service',)))
        ]
    },
    'security/censorship': {
        'authenticat':'authentication', 'crypt':'cryptography', 'secur':'security', 'oauth':'OAuth', 'pyca':'PyCA', 
        'FUNCTIONS':[(lambda d: replace_in(d, 'SSH/SSL/TLS', ('ssh', 'ssl', 'tls')))]},
    'Python language': {
        'abstract base':'abstract base class', 'abstract syntax':'abstract syntax tree',
        ' iter':'iterator', 'introspect':'introspection', 'concurr':'concurrency', ' gil':'GIL',
        ' six':'six', 'context manag':'context manager', 'decimal':'Decimal', 'core': 'core python',
        'FUNCTIONS': [
            (lambda d: replace_in(d, 'abstract base class', (' abc',))),
            (lambda d: replace_in(d, 'python 3', ('python3',))),
            (lambda d: replace_in(d, 'regular expression', ('regex',)))
        ]
    },
    'concurrency': {'tornado':'Tornado', 'twisted':'Twisted', ' event loop':'event loop'},
    'net': {'twisted':'Twisted'},
    'performance': {
        'profil':'profile', ' ram':'RAM', 'dask':'Dask', ' gpu':'GPU', 'cpu':'CPU',
        'efficien':'efficiency', 'optimiz':'optimization', 'ctype':'ctypes', 'swig':'SWIG'},
    'testing': {' bug':'bug', ' test':'test', 'tdd':'TDD', 'lettuce':'Lettuce'},
    'advice': {
        ' tip':'tips', ' trick':'tricks', 'gotcha':'gotchas', 'trade-off':'trade-offs',
        'compar':'compare', 'pitfall':'pitfalls', 'case stud':'case study'
    },
    'other': {
        'arduino':'Arduino', 'robot':'robotics', 'blender':'Blender',
        'FUNCTIONS': [
            (lambda d: replace_in(d, 'internet of things', (' iot ', ' iot.', ' iot,'))),
            (lambda d: replace_in(d, 'art', ('music', 'animation')))
        ]
    }
}
