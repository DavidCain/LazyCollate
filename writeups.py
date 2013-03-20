#!/usr/bin/env python

# David Cain
# 2013-03-20

""" Fetch all writeups for a project and map writeups to users. """

from collections import defaultdict
import getpass

import mechanize

# Strings used by the Confluence system in the HTML for failed login attempts.
# These apply to Confluence 3.5.13 (might need to be updated in later versions).
# If they don't match Confluence errors, failed logins will pass silently
FAILURE_MSG = "Please try again"
CAPTCHA_MSG = "validate your login"


class PageFetch(object):
    def __init__(self, wiki_label, collator=None, cookie_jar="cookies.txt",
                 password=None, force_login=True):
        self.login_url = "https://wiki.colby.edu/login.action"
        self.start_page = "https://wiki.colby.edu/label/" + wiki_label
        self.collator = raw_input("Colby ID: ") if not collator else collator

        self.browser = mechanize.Browser()
        self.cj = mechanize.MozillaCookieJar()
        self.browser.set_cookiejar(self.cj)
        self.cookie_login(cookie_jar, password, force_login)

    def cookie_login(self, cookie_jar, password=None, force_login=True):
        """ Log in if necessary, saving the resulting cookie. """
        if password or force_login:
            self.login(password)
            self.cj.save(cookie_jar, ignore_discard=True, ignore_expires=True)
        else:  # Load a cookie from file
            # NOTE: this should work, but doesn't seem to
            self.cj.load(cookie_jar, ignore_discard=True, ignore_expires=True)

    def login(self, password=None):
        """Repeat the login process until successfully logged in. """
        if not password:
            password = getpass.getpass("Colby password: ")
        while True:
            login_response = self._submit_credentials(password)
            response_lines = login_response.readlines()
            if any(FAILURE_MSG in line for line in response_lines):
                print "Login failed. Please try again"
                password = getpass.getpass("Colby password: ")
            elif any(CAPTCHA_MSG in line for line in response_lines):
                raise Exception("Login requires CAPTCHA! Manually log in at "
                                "%s and re-run to fix" % self.login_url)
            else:
                break  # Login succesful

    def _submit_credentials(self, password):
        """ Submit login and password to Confluence, return page contents. """
        self.browser.open(self.login_url)

        self.browser.select_form(name="loginform")
        self.browser["os_username"] = self.collator
        self.browser["os_password"] = password

        return self.browser.submit()

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
