"""
database
--------

If run as main, this will create the database and define the tables.
Otherwise, it provides the classes to access those tables, and a session:
`database.session`
"""
import os
import re
from collections import namedtuple
from sqlalchemy import create_engine
from sqlalchemy import Column, ForeignKey, Table, UniqueConstraint
from sqlalchemy import Date, Integer, Text
from sqlalchemy.orm import relationship, sessionmaker, validates
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy.types as types


DATABASE = 'sqlite:///' + os.path.join('..', 'data', 'PyCons.db')

# Helper functions
def fix_garbled(text, lookup={}):
    if text is not None and text[0] == text[-1] == '%':
        return text  # Workaround for the ilike('%string%') problem
    if re.search('[^A-Za-z\-\s]', text):
        if text in lookup:
            return lookup[text]
        else:
            tmp = input("Better spelling for {}? ".format(text))
            response = tmp if len(tmp) > 0 else text
            lookup[text] = response
            return response
    else:
        return text

def check_similar_name(new_item):
    cls = type(new_item)
    names = new_item.name.strip().lower().split()
    if names[0] == 'the' and len(names) > 1:
        matcher = "%{}%".format(names[1])
    else:
        if cls.__name__ == 'Human':
            matcher = "% {}%".format(names[-1])
        else:
            matcher = "%{}%".format(names[0])
    filter = cls.name.ilike(matcher)
    possible_matches = session.query(cls).filter(filter).order_by(cls.name).all()  ## TANYA
    if len(possible_matches) == 0:
        return None
    else:
        print("{} has possible matches:".format(new_item))
        print("\t{}".format("\n\t".join(
                "{}: {}".format(*ipm) for ipm in enumerate(possible_matches))))
        tmp = input("Please pick one (or enter if none match): ")
        try:
            i = int(tmp)
            match = possible_matches[i]
            tmp = input("Keep existing name [Y]|n: ")
            if len(tmp) == 0 or tmp.lower() == 'y':
                # Keep the original name
                return match
            else:  # update name
                print("updating the name from {} to {}".format(match.name, new_item.name))
                match.name = new_item.name
                session.add(match)
                session.commit()
                return match
        except (ValueError, IndexError):
            return None

def fetch_or_add(new_item):
    """Return the found item if it exists, or add and return `new_item`.
    """
    required_keys = [
            c.name for c in new_item.__table__.columns
            if c.nullable==False  and not c.name=='id'
    ]
    lookup = dict((k, getattr(new_item, k)) for k in required_keys)
    query = session.query(type(new_item)).filter_by(**lookup)
    result = query.first()
    if result is None:
        # Check for different name spelling
        if 'name' in lookup and not isinstance(new_item, Conference):
            result = check_similar_name(new_item)
        if result is None:
            session.add(new_item)
            session.commit()
            return new_item
        # Update additional new data
    additional_keys = [c.name for c in new_item.__table__.columns
                       if c.nullable==True]
    for k in additional_keys:
        setattr(result, k, getattr(new_item, k))
    session.commit()
    return result

TalkData = namedtuple(
        'TalkData',
        ['speaker_names', 'topic_names', 'organization_names']
)
TalkData.__doc__ = "Reduce typos by providing a namedtuple"


def add_talk(talk, speaker_names=[], topic_names=[], organization_names=[]):
    """Use this instead of `fetch_or_add` for the `Talk` class.
    
    It assumes the lists of names are all just strings, and fetches/creates
    each of the speakers, topics, and organizations to the database after
    adding the talk.
    
    To avoid typos, use the `TalkData` namedtuple to contain the `*.names`
    items, and then use the call like this::
    
        d = TalkData(['Trillian'], ['Heart of Gold'], ['Sirius Cybernetics'])
        add_talk(Talk(title="Infinity Drives", conference_id=1), **d._asdict())
    """
    talk = fetch_or_add(talk)
    for name in speaker_names:
        speaker = fetch_or_add(Human(name=name))
        talk.speakers.append(speaker)
    for name in [n.lower() for n in topic_names]:
        topic = fetch_or_add(Topic(topic=name))
        talk.topics.append(topic)
    for name in organization_names:
        organization = fetch_or_add(Organization(name=name))
        talk.companies.append(organization)
    session.commit()


class ProperName(object):
    """Removes the honorific and then capitalizes when appropriate.
    """
    # This is a class because I originally thought using a TypeDecorator and a
    # specially  typed column were the way to go here. But it messed up glob
    # queries (WHERE name LIKE '%foo%';) and I switched to @validates.
    # ... just never refactored ~ Tanya
    @staticmethod
    def capitalize(name_segment):
        return "-".join(n.capitalize() for n in name_segment.split("-"))

    @staticmethod 
    def cleanup(raw_name):
        names = ''.join(raw_name.split('.')).strip().lower().split()
        if len(names) == 0:
            raise(ValueError, "Zero length ProperName is not allowed.")
        # Honorific
        honorifics = ("dr", "mr", "mrs", "ms", "mz", "miss")
        if names[0] in honorifics:
            names = names[1:]
        # Always capitalize the first name
        names[0] = names[0].capitalize()
        # Particles and prefixes
        particles = (
                "da", "de", "di", "do", "du", "le", "la",
                "auf", "van", "von", "der", "ter", "tor")
        prefixes = ("al-", "el-", "d'", "l'", "mc", "mac", "o'")
        for i in range(1, len(names)):
            # Skip the particles
            if i < (len(names)-1) and names[i] not in particles:
                if any(names[i].startswith(p) for p in prefixes):
                    for p in prefixes:
                        if names[i].startswith(p):
                            suffix = ProperName.capitalize(
                                    names[i].split(p, 1)[-1])
                            if p in ("mc", "mac", "o'"):
                                p = p.capitalize()
                            names[i] = p + suffix
                            break
                else:
                    names[i] = ProperName.capitalize(names[i])
            elif names[i] not in particles:
                names[i] = ProperName.capitalize(names[i])
        fixed_name = " ".join(names)
        return fix_garbled(fixed_name)


Base = declarative_base()

# Association tables for many-to-many relationships
talk_topic = Table('talk_topic', Base.metadata,
    Column('talk_id', Integer,
            ForeignKey('talk.id'), primary_key=True, nullable=False),
    Column('topic_id', Integer,
            ForeignKey('topic.id'), primary_key=True, nullable=False))


class HumanInvolvement(Base):
    __tablename__ = 'human_involvement'
    id = Column(Integer, primary_key=True)
    human_id = Column(Integer, ForeignKey('human.id'), nullable=False)
    conference_id = Column(Integer, ForeignKey('conference.id'))
    talk_id = Column(Integer, ForeignKey('talk.id'))
    __table_args__ = (UniqueConstraint('human_id', 'conference_id', 'talk_id'), )

class OrganizationInvolvement(Base):
    __tablename__ = 'organization_involvement'
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    conference_id = Column(Integer, ForeignKey('conference.id'))
    talk_id = Column(Integer, ForeignKey('talk.id'))
    __table_args__ = (UniqueConstraint('organization_id', 'conference_id', 'talk_id'), )


# Remaining tables
class Conference(Base):
    __tablename__ = 'conference'
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    country = Column(Text, nullable=False)
    url = Column(Text)
    begin_date = Column(Date)
    end_date = Column(Date)
    talks = relationship("Talk", back_populates="conference")
    sponsors = relationship(
            "Organization",
            secondary=OrganizationInvolvement.__tablename__,
            primaryjoin="and_("
                        "Conference.id==OrganizationInvolvement.conference_id,"
                        "OrganizationInvolvement.talk_id==None)",
            secondaryjoin="OrganizationInvolvement.organization_id==Organization.id",
            back_populates="sponsorships")
    volunteers = relationship(
            'Human',
            secondary=HumanInvolvement.__tablename__,
            primaryjoin="and_("
                        "Conference.id==HumanInvolvement.conference_id,"
                        "HumanInvolvement.talk_id==None)",
            secondaryjoin="HumanInvolvement.human_id==Human.id",
            back_populates="volunteering")
    __table_args__ = (UniqueConstraint('year', 'name'),)
    
    def __repr__(self):
        return "<Conference(name='{}', year={})>".format(self.name, self.year)


class Talk(Base):
    __tablename__ = 'talk'
    # available talk categories
    KEYNOTE = 'keynote'
    PANEL = 'panel'
    PLENARY = 'plenary'
    POSTER = 'poster'
    TALK = 'talk'
    TUTORIAL = 'tutorial'
    id = Column(Integer, primary_key=True)
    conference_id = Column(Integer, ForeignKey('conference.id'), nullable=False)
    title = Column(Text, nullable=False)
    level = Column(Text)
    category = Column(Text)
    abstract = Column(Text)
    video_url = Column(Text)
    slides_url = Column(Text)
    code_url = Column(Text)
    conference = relationship('Conference', back_populates='talks')
    # Many-to-Many
    topics = relationship('Topic', secondary=talk_topic, back_populates='talks')
    speakers = relationship('Human', secondary=HumanInvolvement.__tablename__,
            primaryjoin="and_(Talk.id==HumanInvolvement.talk_id)",
            secondaryjoin="HumanInvolvement.human_id==Human.id",
            back_populates='talks')
    companies = relationship('Organization', secondary=OrganizationInvolvement.__tablename__,
            primaryjoin="and_(Talk.id==OrganizationInvolvement.talk_id)",
            secondaryjoin="OrganizationInvolvement.organization_id==Organization.id",
            back_populates='talks')
    # Additional constraints
    __table_args__ = (UniqueConstraint('conference_id', 'title'),)
    
    def __repr__(self):
        if self.conference is None:
            return "<Talk(title='{}' <not yet bound>)>".format(self.title)
        else:
            return "<Talk(title='{}', conference='{} {}')>".format(
                    self.title, self.conference.name, self.conference.year)
    
    @validates('title', 'category', 'abstract')
    def validate_text(self, key, txt):
        return None if txt is None else re.sub(r'\s+', ' ' , txt.strip())


class Topic(Base):
    __tablename__ = 'topic'
    id = Column(Integer, primary_key=True)
    topic = Column(Text, unique=True, nullable=False)
    # MANY-TO-MANY  with Talk
    talks= relationship('Talk', secondary=talk_topic, back_populates='topics')
    
    def __repr__(self):
        return "<Topic(topic='{}')>".format(self.topic)
    
    @validates('topic')
    def validate_text(self, key, txt):
        return None if txt is None else re.sub(r'\s+', ' ' , txt.strip())


class Human(Base):
    __tablename__ = 'human'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)  # 'unique' --> trouble?
    # Many-to-Many with Talk via HumanInvolvement
    # Many-to-Many with Conference via HumanInvolvement
    volunteering = relationship(
            'Conference',
            secondary=HumanInvolvement.__tablename__,
            primaryjoin="and_(Human.id==HumanInvolvement.human_id, HumanInvolvement.talk_id==None)",
            secondaryjoin="HumanInvolvement.conference_id==Conference.id",
            back_populates="volunteers")
    talks = relationship(
            'Talk',
            secondary=HumanInvolvement.__tablename__,
            back_populates="speakers")
    
    def __repr__(self):
        return "<Human(name='{}')>".format(self.name)
    
    @validates('name')
    def validates_name(self, key, value):
        return ProperName.cleanup(value)


class Organization(Base):
    __tablename__ = 'organization'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    # Many-to-Many with Talk via OrganizationInvolvement
    # Many-to-Many with Conference via OrganizationInvolvement
    sponsorships = relationship(
            "Conference",
            secondary=OrganizationInvolvement.__tablename__,
            primaryjoin="and_("
                        "Organization.id==OrganizationInvolvement.organization_id,"
                        "OrganizationInvolvement.talk_id==None)",
            secondaryjoin="OrganizationInvolvement.conference_id==Conference.id",
            back_populates="sponsors")
    talks = relationship(
            'Talk',
            secondary=OrganizationInvolvement.__tablename__,
            back_populates="companies")
    
    def __repr__(self):
        return "<Organization(name='{}')>".format(self.name)
    
    @validates('name')
    def validate_text(self, key, txt):
        return None if txt is None else re.sub(r'\s+', ' ' , txt.strip())



if __name__ == '__main__':
    import inspect
    import sqlite3
    views_file = 'create_views.sql'
    path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    if not os.path.exists(views_file):
        msg = ('Sorry. This script must be run from {} '
                'so the database is in the right place.')
        exit(msg.format(path))
    engine = create_engine(DATABASE, echo=True)
    Base.metadata.create_all(engine)
    conn = sqlite3.connect(DATABASE.split(':///')[-1])
    query = open(views_file).read()
    conn.executescript(query)
    conn.commit()
    conn.close()
else:
    engine = create_engine(DATABASE)
    Session = sessionmaker(bind=engine)
    session = Session()
