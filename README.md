# LazyCollate

Each semester, some 70 students enroll in Colby College's CS 151. A student
worker is tasked with collating each week's projects into a sensible directory
structure, including each student's writeup rendered as a PDF.

I'm lazy, so I wrote a program to automate this procedure.

Working off a project number and a list of students, LazyCollate locates
the students' code on a network share and renders Confluence pages using
either [QtWebKit][qtwebkit] or [PhantomJS][phantomjs]. File renaming,
content warnings, and web scraping are all done automatically.

# Installation and setup

## Dependencies

LazyCollate is tested on a GNU/Linux system, but should be cross-platform.

The versions within your operating system's package manager will most likely be fine.

### Core dependencies
- Python 2.7
- [`mechanize`][mechanize] (tested on 2.5)
- [`wkhtmltopdf`][wkhtmltopdf] (tested on 0.9.9)
    - [PhantomJS][phantomjs] can optionally be used in place of `wkhtmltopdf`
    (tested on version 1.9.0, statically compiled on 2013-02-12 from
    [`04368c6af`][phantom-commit])
- [BeautifulSoup][beautiful_soup] (version 3 or 4 okay)


## Configuration
1. Mount the CS 151 network share to `/mnt/CS151` (or elsewhere, but change
   `CS151_MOUNT_POINT` in `collate.py` if you do so).

2. Optionally change any of the global variables within `collate.py`.

## Instructions

### Basic usage:

First, create a file `students.txt` with each CS151 student's Colby ID on its
own line.

Then, to collate project 2, call:

    $ python collate.py 2 students.txt

LazyCollate will ask for your password and log in for you. Then, sit back while
it does the rest!

### Logging

LazyCollate writes out to the comprehensive `collation.log`. The `--verbose`
flag will ensure that all messages permeate to standard output in addition to
this log file.

## Other options

To see all available options:

    $ python collate.py --help

## Maintenance

This section is aimed at future maintainers of LazyCollate.

LazyCollate is designed to work with Atlassian Confluence 3.5.13's login
system. If failed login error messages change, or if the HTML login form changes
name or field names, `writeups.py` will need to be modified accordingly.

Cookie-based logins with `wkhtmltopdf` don't work currently. The active workaround
is to just `POST` the username and password with a redirect for the desired
page (such as in `save_writeup()` in `collate.py`). See `cookie_login()` in
`writeups.py` for where cookies should work.



[mechanize]: http://pypi.python.org/pypi/mechanize/
[phantomjs]: https://github.com/ariya/phantomjs
[phantom-commit]: https://github.com/ariya/phantomjs/commit/04368c6af8110280c8d7e2cedfe710065c672e4a
[qtwebkit]: http://qt-project.org/wiki/QtWebKit
[wkhtmltopdf]: https://github.com/antialize/wkhtmltopdf
[beautiful_soup]: http://www.crummy.com/software/BeautifulSoup/
