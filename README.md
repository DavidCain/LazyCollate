# LazyCollate

Each semester, some 70 students enroll in Colby College's CS 151. A student
worker (that'd be me) is tasked with collating each week's projects into a
sensible directory structure, including each student's writeup rendered as a
PDF.

I'm lazy, so I wrote a program to automate this procedure.

Working off a project number and a list of students, LazyCollate locates
the students' code on a network share and renders Confluence pages using
either [QtWebKit][qtwebkit] or [PhantomJS][phantomjs]. File renaming,
content warnings, and web scraping are all done automatically.

# Installation and setup

## Dependencies
Other versions will likely work, but LazyCollate is tested with:

- Python 2.7
- [`mechanize`][mechanize] v 2.5
- [`wkhtmltopdf`][wkhtmltopdf] 0.9.9
- [PhantomJS][phantomjs] 1.9.0 (statically compiled on 2012-02-12 from
  [04368c6af][phantom-commit])

## Configuration
1. Mount the CS 151 network share to `/mnt/CS151` (or elsewhere, but change
   `CS151_MOUNT_POINT` in `collate.py` if you do so).

2. If you're not me and/or unable to steal my password, you'll probably want to
   set `OS_USERNAME` to your Colby ID.

## Instructions

### Basic usage:

First, create a file `students.txt` with each CS151 student's Colby ID on its
own line.

Then, to collate project 2, call:

    $ python collate.py 2 students.txt

If the specified arguments are correct, LazyCollate will ask once for your
password. Then, sit back while it does the rest!

## Other options

The `--verbose` flag will print human-readable warnings and error messages, as
well as some information from the PDF-rendering toolkit.

To see all available options:

    $ python collate.py --help


[mechanize]: http://pypi.python.org/pypi/mechanize/
[phantomjs]: https://github.com/ariya/phantomjs
[phantom-commit]: https://github.com/ariya/phantomjs/commit/04368c6af8110280c8d7e2cedfe710065c672e4a
[qtwebkit]: http://qt-project.org/wiki/QtWebKit
[wkhtmltopdf]: https://github.com/antialize/wkhtmltopdf
