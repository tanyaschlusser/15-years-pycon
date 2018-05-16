"""Script to run all of the acquisition files that populate the database.

Note that afterward I had to go through and fix some typos in company names
and some duplicate human names that were missed (like with/without initials
and other stuff).



"""
import glob
import inspect
import os
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 


msg = ("Just download the SQLite3 database? (default, easier) or else run the data acquisition (tedious)?\n"
        "Just download? [Y]n  ")
response = input(msg)
download_instead = True if response == '' or response[0] in ('', 'Y', 'y') else False
destination = os.path.join(parentdir, 'data', 'PyCons.db')

if download_instead:
    from urllib import request
    print("Downloading the existing database from Dropbox.")
    url = 'https://www.dropbox.com/s/3muutb5uw15g5tp/PyCons.db?dl=1'
    req = request.urlopen(url)
    content = req.read()
    with open(destination, 'wb') as outfile:
        outfile.write(content)
else:
    if not os.path.exists(destination):
        print("Creating the database.")
        wd = os.getcwd()
        os.chdir(os.path.join(parentdir, 'data'))
        with open('database.py') as script:
            exec(script.read())
        os.chdir(wd)
    print("Running the data acquisition scripts.")
    for fname in glob.glob('get*.py'):
        with open(fname) as script:
            exec(script.read())

print("Done. Content is in  {}".format(destination))
