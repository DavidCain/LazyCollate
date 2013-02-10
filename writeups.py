#!/usr/bin/env python
# David Cain
# 2013-02-08

""" A script to fetch all writeups for a project. """

import getpass
import mechanize


class PageFetch(object):
    def __init__(self, wiki_label, collator="djcain"):
        self.login_url = "https://wiki.colby.edu/login.action?os_destination=%2Flabel%2F" + wiki_label
        self.collator = raw_input("Username:") if not collator else collator

        self.browser = mechanize.Browser()
        self.login()

    def login(self):
        self.browser.open(self.login_url)

        self.browser.select_form(name="loginform")
        self.browser["os_username"] = self.collator
        self.browser["os_password"] = getpass.getpass()
        results = self.browser.submit()  # TODO: no verification that successful

    def get_all_writeups(self):
        """ Starting on a page with writeups, yield all pages until exhausted. """
        assert self.browser, "Browser already closed, as links exhausted."
        while True:
            for link in self.browser.links(predicate=self._is_writeup):
                yield link.absolute_url
            if not self._next_page():
                self.browser.close()
                break

    def _is_writeup(self, link):
        # Pretty hackish, but there's little HTML to indicate what's a page and
        # what's not
        return "display" in link.url and self.collator not in link.url

    def _next_page(self):
        try:
            self.browser.follow_link(text_regex="Next >>")
        except mechanize.LinkNotFoundError:
            return False
        else:
            return True


def get_writeups(label):
    p = PageFetch(label)
    return list(p.get_all_writeups())


if __name__ == "__main__":
    for url in get_writeups("cs151s13project1"):
        print url
