pragma foreign_keys = off;

DROP TABLE IF EXISTS Media;
DROP TABLE IF EXISTS Writer;
DROP TABLE IF EXISTS WriterMedia;

PRAGMA foreign_keys = ON;

CREATE TABLE Media (
    name text,
    year text,
    director text,
    animationProduction text,

    PRIMARY KEY (name)
);

CREATE TABLE Writer (
    name text,

    PRIMARY KEY (name)
);

CREATE TABLE WriterMedia (
    writer text,
    media text,

    PRIMARY KEY (media,writer),
    
    FOREIGN KEY (media) REFERENCES Media(name) ON UPDATE CASCADE ON DELETE CASCADE,

    FOREIGN KEY (writer) REFERENCES Writer(name) ON UPDATE CASCADE ON DELETE CASCADE
);

INSERT INTO Media VALUES
    ('Barbie in the Nutcracker','2001','Owen Hurley','Mainframe Entertainment'),
    ('Barbie as the Princess and the Pauper','2002','William Lau','Mainframe Entertainment'),
    ('Barbie in the 12 Dancing Princesses','2006','Eric Fogel','Mainframe Entertainment');

INSERT INTO Writer VALUES
    ('Rob Hudnut'),
    ('Linda Engelsiepen'),
    ('Elana Lesser'),
    ('Cliff Ruby'),
    ('Hilary Hinkle');

INSERT INTO WriterMedia VALUES
    ('Rob Hudnut','Barbie in the Nutcracker'),
    ('Linda Engelsiepen','Barbie in the Nutcracker'),
    ('Hilary Hinkle','Barbie in the Nutcracker'),
    ('Elana Lesser','Barbie as the Princess and the Pauper'),
    ('Cliff Ruby','Barbie as the Princess and the Pauper'),
    ('Elana Lesser','Barbie in the 12 Dancing Princesses'),
    ('Cliff Ruby','Barbie in the 12 Dancing Princesses');


