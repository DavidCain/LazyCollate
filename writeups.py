#!/usr/bin/env python

# David Cain
# 2013-03-20

""" Fetch all writeups for a project and map writeups to users. """

from collections import defaultdict

import mechanize

import confl


class PageFetch(confl.AccessConfluence):
    def __init__(self, wiki_label, *args, **kwargs):
        self.start_page = "https://wiki.colby.edu/label/" + wiki_label
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
        return "display" in link.url and self.collator not in link.url

    def _next_page(self):
        try:
            self.browser.follow_link(text_regex="Next >>")
        except mechanize.LinkNotFoundError:
            return False
        else:
            return True


def extract_colbyid(writeup_url):
    """ Extract the Colby ID from a writeup URL.

    Example: "srtaylor" from:
        https://wiki.colby.edu/display/~srtaylor/CS151+Project+1
    """
    id_prefix = "/display/~"  # The string that should precede the Colby ID
    display_url = writeup_url[writeup_url.find(id_prefix) + len(id_prefix):]
    return display_url[:display_url.find("/")]


def writeup_by_id(writeup_urls):
    """ Return dict where keys are Colby ID's, each value a list of pages. """
    writeups_dict = defaultdict(list)
    for writeup_url in writeup_urls:
        author = extract_colbyid(writeup_url)
        writeups_dict[author].append(writeup_url)
    return dict(writeups_dict)


if __name__ == "__main__":
    p = PageFetch("cs151s13project1")
    for url in p.get_all_writeups():
        print url
