#!/usr/bin/env python
# David Cain
# 2013-02-11

""" Fetch all writeups for a project and map writeups to users. """

from collections import defaultdict
import getpass
import mechanize
import os


class PageFetch(object):
    def __init__(self, wiki_label, collator="djcain", cookie_jar="cookies.txt",
                 force_login=True):
        self.login_url = "https://wiki.colby.edu/login.action"
        self.start_page = "https://wiki.colby.edu/label/" + wiki_label
        self.collator = raw_input("Username:") if not collator else collator

        self.browser = mechanize.Browser()
        self.cj = mechanize.MozillaCookieJar()
        self.browser.set_cookiejar(self.cj)
        self.login(cookie_jar, force_login)

    def login(self, cookie_jar, force_login=True):
        if not force_login and cookie_jar and os.path.isfile(cookie_jar):
            self.cj.load(cookie_jar, ignore_discard=True, ignore_expires=True)
        else:  # Login, save to cookie
            self.browser.open(self.login_url)

            self.browser.select_form(name="loginform")
            self.browser["os_username"] = self.collator
            self.browser["os_password"] = getpass.getpass()

            results = self.browser.submit()  # TODO: no verification that successful
            self.cj.save(cookie_jar, ignore_discard=True, ignore_expires=True)

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


def get_writeups(label):
    p = PageFetch(label)
    return list(p.get_all_writeups())


def get_colbyid(writeup_url):
    """ Extract the Colby ID from a writeup URL.

    Example: "srtaylor" from:
        https://wiki.colby.edu/display/~srtaylor/CS151+Project+1
    """
    display_url = writeup_url[writeup_url.find("/display/~") + 10:]
    return display_url[:display_url.find("/")]


def writeup_by_id(writeup_urls):
    writeups_dict = defaultdict(list)
    for writeup_url in writeup_urls:
        author = get_colbyid(writeup_url)
        writeups_dict[author].append(writeup_url)
    return dict(writeups_dict)


if __name__ == "__main__":
    p = PageFetch("cs151s13project1")
    for url in p.get_all_writeups():
        print url
