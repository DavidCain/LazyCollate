# David Cain
# 2013-05-12

""" Access the Confluence wiki system, saving the login cookie. """

import getpass

import mechanize

# Strings used by the Confluence system in the HTML for failed login attempts.
# These apply to Confluence 3.5.13 (might need to be updated in later versions).
# If they don't match Confluence errors, failed logins will pass silently
FAILURE_MSG = 'Please try again'
CAPTCHA_MSG = 'validate your login'


class AccessConfluence(object):
    """ Log into the system, maintain login information in cookies. """
    def __init__(self, collator=None, cookie_jar='cookies.txt',
                 password=None, force_login=True):
        self.login_url = 'https://wiki.colby.edu/login.action'
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
        """ Repeat the login process until successfully logged in. """
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

        self.browser.select_form(name='loginform')
        self.browser['os_username'] = self.collator
        self.browser['os_password'] = password

        return self.browser.submit()
