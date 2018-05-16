# Processing.py project

This directory contains a Processing.py project.
Processing.py (http://py.processing.org/) is an optional Jython mode
for Ben Fry's Processing -- a Java desktop application that provides
simple commands for drawing and animation, and is popular in education.

This directory is independent of the rest of the GitHub repo.
You do not need to `pipenv install --skip-lock` anything at all
if you just want to make the plots; just install Processing.


## Licensed content

Please see the top-level directory
[LICENSED_CONTENT](https://github.com/tanyaschlusser/15-years-pycon/tree/master/LICENSED_CONTENT)
for a list of all licensed content used to make this poster.


## Instructions

To run the Processing code and recreate the poster, you must first
install Processing, and then install the Jython add-on. For detailed
instructions, visit
the [Processing.py 'getting started' page](http://py.processing.org/tutorials/gettingstarted/).

If you want to skip those instructions, do this:

* Download Processing [(download page)](http://processing.org/download), unzip it, and put
  it where you want it.
* Open Processing, click the button in the top right corner, and select 'Add mode...'.
  It will open a window where you can install Jonathan Feinberg's Python mode for Processing.

The Processing.py documentation is very good. Here are direct links:

* Function reference: http://py.processing.org/reference/
* Tutorials: http://py.processing.org/tutorials/


## Directory structure

The primary project file has the extension `*.pyde`.
Additional files are regular `*.py`, and resources are stored in the
`data/` directory.

To open this project, first open Processing, then navigate to
*File → Open...* and select `pycon2018_poster.pyde`.

* `datasets.py` imports all of the data for use in the main code.
* `img.py` imports all of the images and provides a class for easier placement and scaling.
* `util.py` provides the hand-drawn pen style and the other complicated
            drawings (map/bars/cluster little stick figures).


## Memory

The Java Virtual Machine has a low memory cap of 1GB (I think) initially.
If you have more than a couple of images to import, you may run into a memory error.
In that case, navigate to *Processing → Preferences...* and edit the maximum available
memory setting.

Java error messages were hard to diagnose, so we'd run broken code snippets in a
CPython interpreter to debug.


## Dots Per Inch

The 300 DPI version failed to print, but the 125 DPI version was OK.
It could be a memory thing -- I think the limit is about 21-25 MB for a poster printer.

You may need to edit the PDF to add a scale to the dictionary:
* Actually the file opens fine without it, but...
* There is a dictionary at the end, enclosed in double angle braces. It starts
  with `<</Contents ... [etc] >>`
* Add a final entry to the dictionary. For 125 DPI it is `/UserUnit 0.576`
 which indicates a scaling factor relative to the standard 72 DPI: (72 / 0.576 = 125).
* This is what the very end of mine looks like:

### Before

```
<</Contents 280 0 R/ [all kinds of stuff] /MediaBox[0 0 8250 5000]>>
```

### After

```
<</Contents 280 0 R/ [all kinds of stuff] /MediaBox[0 0 8250 5000]/UserUnit 0.576>>
```

