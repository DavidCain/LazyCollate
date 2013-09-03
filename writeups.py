#!/usr/bin/env python

# David Cain
# 2013-05-12

""" Fetch all writeups for a project and map writeups to users. """

from collections import defaultdict
import re

import mechanize

import confl


# First group should be the Colby ID (extracted from a display URL)
USER_REGEX = re.compile(r'.colby.edu/display/~([a-z]+)/')


class PageFetch(confl.AccessConfluence):
    def __init__(self, wiki_label, *args, **kwargs):
        self.start_page = 'https://wiki.colby.edu/label/' + wiki_label
        confl.AccessConfluence.__init__(self, *args, **kwargs)

    def get_all_writeups(self):
        """ Starting on a page with writeups, yield all pages until exhausted. """
        self.browser.open(self.start_page)
        while True:
            for link in self.browser.links(predicate=self._is_writeup):
                yield link.absolute_url
            if not self._next_page():
                break

    def _is_writeup(self, link):
        # hackish, but there's little to indicate what's a page and what's not
        return 'display' in link.url and self.collator not in link.url

    def _next_page(self):
        try:
            self.browser.follow_link(text_regex='Next >>')
        except mechanize.LinkNotFoundError:
            return False
        else:
            return True


def extract_colbyid(writeup_url):
    """ Extract the Colby ID from a writeup URL.

    Example: 'srtaylor' from:
        https://wiki.colby.edu/display/~srtaylor/CS151+Project+1
    """
    try:
        return USER_REGEX.search(writeup_url).group(1)
    except AttributeError:
        raise ValueError("Cannot extract Colby ID from %s" % writeup_url)


def writeup_by_id(writeup_urls):
    """ Return dict where keys are Colby ID's, each value a list of pages. """
    writeups_dict = defaultdict(list)
    for writeup_url in writeup_urls:
        try:
            author = extract_colbyid(writeup_url)
        except ValueError as e:
            print e.message, "(omitting writeup from list)."
        else:
            writeups_dict[author].append(writeup_url)
    return dict(writeups_dict)


if __name__ == '__main__':
    p = PageFetch('cs151s13project1')
    for url in p.get_all_writeups():
        print url
