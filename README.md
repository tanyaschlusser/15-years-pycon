# 15 years of PyCon

Thank you for your interest in our [poster](https://bit.ly/15-years-pycon)!
This repo contains code to reproduce the analysis and visualization.

## License notice

Some content in this repo is not ours, and the MIT license does not apply to
that content. Please see the directory `LICENSED_CONTENT` for identification
of licensed content and to read their respective licenses.

## Setup

If all you want to do is see how to make the poster, skip to the
[visualization](#visualization) section.

Otherwise, for the analysis, you will need Python 3.5+ because
I used print as a function and probably other things. If you use Python 3.4,
you can't call `help()` on some things in SQLAlchemy because of a thing about
`inspect.py` that's gone in 3.5+. I didn't realize that until cleaning
up this repo for sharing though, so everything worked OK on 3.4.

```
pipenv --three
pipenv install --skip-lock
pipenv shell
# and `exit` to exit...
```

Enter each directory to do the relevant work for each step.


<a href="#data" name="data">#</a> <b>data</b>

This directory will contain the database (it's 30MB so it's on Dropbox not GitHub),
plus the SQLAlchemy ORM. You don't need to directly run anything in here; the path
to `database.py` is prepended to the Python path in both `acquisition` and `analysis`.


<a href="#acquisition" name="acquisition">#</a> <b>acquisition</b>

This directory contains a script `run_all_acquisitions.py` to run the data
acquisition or download the database from Dropbox; it gives an interactive
choice. It will put the database in `data/PyCons.db`.

Scraping is partly manual to deal with different spellings of names, so
expect to spend an hour or two answering 'Y' or 'n' to questions like
'is Enthought' the same as 'Enthought, LLC.'?


<a href="#analysis" name="analysis">#</a> <b>analysis</b>


<a href="#visualization" name="visualization">#</a> <b>visualization</b>

This directory is independent of the rest of the project.
If all you want to do is reproduce the poster, go
[there](https://github.com/tanyaschlusser/15-years-pycon/tree/master/visualization)
and follow the instructions. You do not need to `pipenv install` anything.
