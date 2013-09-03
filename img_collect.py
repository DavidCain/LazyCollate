# David Cain
# 2013-05-11

""" Download all images from wiki pages. """

import os
import re
import urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:
    from BeautifulSoup import BeautifulSoup  # Syntax is bs3-compatible

import confl


# Match URLs for user-uploaded images (used to ignore other images)
USER_IMG_REGEX = re.compile("^/download/attachments/.*$")


class ImageSaver(confl.AccessConfluence):
    """ Save images from a wiki writeup to a local directory. """
    def __init__(self, dest_dir, *args, **kwargs):
        self.dest_dir = dest_dir
        confl.AccessConfluence.__init__(self, *args, **kwargs)

    def save_images(self, writeup_url, prefix=""):
        """ Save all user-uploaded images on a wiki page to the directory. """
        soup = BeautifulSoup(self.browser.open(writeup_url))
        user_images = soup.find_all("img", attrs={"src": USER_IMG_REGEX})

        for image in user_images:
            image_url = urlparse.urljoin("https://wiki.colby.edu/", image["src"])
            self.download_image(image_url, prefix)

    def download_image(self, image_url, prefix=""):
        """ Download the image, prependeng an optional prefix to the filename. """
        parse_result = urlparse.urlparse(image_url)

        # Make a path on the disk from the Colby ID and image URL
        # Replace special characters that break retrieve() (non-exhaustive)
        orig_fn = os.path.split(parse_result.path)[1]
        dest_fn = prefix + re.sub("[*?|<>]", "-", orig_fn)
        dest_path = os.path.join(self.dest_dir, dest_fn)

        self.browser.retrieve(image_url, dest_path)
