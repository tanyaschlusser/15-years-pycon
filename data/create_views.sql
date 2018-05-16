-- Manually make some views to more easily inspect data.

CREATE VIEW IF NOT EXISTS view_talks_humans_topics AS
  SELECT
    c.name AS conference,
    c.year AS year,
    c.location AS location,
    ta.title AS title,
    hu.name AS speaker,
    tp.topic AS topic
  FROM talk AS ta
    JOIN conference AS c ON ta.conference_id = c.id
    JOIN human_involvement AS hi ON ta.id = hi.talk_id
    JOIN human AS hu ON hi.human_id = hu.id
    LEFT JOIN talk_topic AS tt ON ta.id = tt.talk_id
    LEFT JOIN topic AS tp ON tt.topic_id = tp.id;

CREATE VIEW IF NOT EXISTS view_talks_orgs_topics AS
  SELECT
    c.name AS conference,
    c.year AS year,
    c.location AS location,
    ta.title AS title,
    org.name AS organization,
    tp.topic AS topic
  FROM talk AS ta
    JOIN conference AS c ON ta.conference_id = c.id
    JOIN organization_involvement AS oi ON ta.id = oi.talk_id
    JOIN organization AS org ON oi.organization_id = org.id
    LEFT JOIN talk_topic AS tt ON ta.id = tt.talk_id
    LEFT JOIN topic AS tp ON tt.topic_id = tp.id;

CREATE VIEW IF NOT EXISTS view_sponsors AS
  SELECT
    c.name AS conference,
    c.year AS year,
    c.location AS location,
    org.name AS sponsor
  FROM conference AS c
    JOIN organization_involvement AS oi on c.id = oi.conference_id
    JOIN organization AS org ON oi.organization_id = org.id;
