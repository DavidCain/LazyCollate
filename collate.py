#!/usr/bin/env python

# David Cain
# 2013-05-16

""" Automatically collate projects for CS151 students.

See the accompanying README.md for instructions.
"""

import datetime
import getpass
import logging
import logging.handlers
import os
import re
import shutil
import subprocess
import sys
import urllib

import writeups
from img_collect import ImageSaver


# Global variables that are meant to be customized
# The rest of this file should be able to remain unmodified
# ----------------------------------------
CS151_MOUNT_POINT = "/mnt/CS151"
COLLATED_DIR = "/mnt/CS151/Collated/"
IMAGES_DIR = "/mnt/CS151/Images/"
OS_USERNAME = None  # Collator's Colby ID (for easier use)
PDF_PRINTER = "wkhtmltopdf"  # (or phantomjs)
# ----------------------------------------


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# Log all messages to file
descriptive = logging.Formatter('%(asctime)s -  %(levelname)s - %(message)s')
master_handler = logging.handlers.RotatingFileHandler("collation.log",
                                                      maxBytes=500 * 1024,
                                                      backupCount=10)
master_handler.setFormatter(descriptive)
master_handler.setLevel(logging.DEBUG)
log.addHandler(master_handler)

# Print info messages to stdout
stdout_info = logging.StreamHandler(sys.stdout)
stdout_info.setLevel(logging.INFO)
log.addHandler(stdout_info)


class ProjectWarning(Exception):
    """A generic warning about the project."""
    pass


class AbsentWriteup(ProjectWarning):
    """No writeup was found."""
    label = "NO_WRITEUP"


class AbsentProject(ProjectWarning):
    """No project was found."""
    label = "NO_PROJECT"


class MultipleProjects(ProjectWarning):
    """Multiple projects are labeled."""
    label = "MULTIPLE_PROJS"


class Project(object):
    """ Store attributes about a single CS151 project. """
    def __init__(self, proj_num):
        self.proj_regex = make_proj_regex(proj_num)
        self.set_wiki_label(proj_num)
        self.proj_num = proj_num

    def set_wiki_label(self, proj_num):
        now = datetime.datetime.now()
        semester = "s" if now.month < 7 else "f"  # spring/fall semester
        year = now.year % 100  # (e.g. 13)
        self.wiki_label = "cs151%s%dproject%d" % (semester, year, proj_num)

    def match(self, dirname):
        return self.proj_regex.match(os.path.split(dirname)[1])


class Collate(object):
    """ Collate all students' work for a given project. """
    def __init__(self, proj_num):
        self.project = Project(proj_num)
        login_info = {"collator": OS_USERNAME, "password": OS_PASSWORD}

        fetch = writeups.PageFetch(self.project.wiki_label, **login_info)
        writeup_urls = list(fetch.get_all_writeups())
        self.writeups_dict = writeups.writeup_by_id(writeup_urls)

        self.collated_proj_dir = self.make_dest_dir(COLLATED_DIR, proj_num)
        image_dir = self.make_dest_dir(IMAGES_DIR, proj_num)
        self.image_saver = ImageSaver(image_dir, **login_info)

    def make_dest_dir(self, dir_root, proj_num):
        """ Create a fresh directory to store results of collation run. """
        dir_path = os.path.join(dir_root, "Proj%d" % proj_num)
        self._reset_dir(dir_path)
        return dir_path

    def _reset_dir(self, dir_path):
        """ Create the directory, erasing contents if it exists. """
        if os.path.isdir(dir_path):
            print "About to delete '%s'" % dir_path
            print "Press Enter to continue, Ctrl+C to abort"
            raw_input()
            shutil.rmtree(dir_path)
            log.debug("Removed existing dir '%s'", dir_path)
        os.mkdir(dir_path)

    def collate_projects(self, students):
        for colby_id in students:
            try:
                writeup_urls = self.writeups_dict[colby_id]
            except KeyError:
                writeup_urls = []

            stu = StudentCollate(colby_id, self.project, writeup_urls,
                                 self.collated_proj_dir)
            stu.collect()

    def save_all_images(self, students):
        log.info("Saving all wiki images for all students with wiki pages.")
        for colby_id in students:
            try:
                writeup_urls = self.writeups_dict[colby_id]
            except KeyError:
                continue  # No writeups to extract images from

            for writeup_url in writeup_urls:
                self.image_saver.save_images(writeup_url, prefix=colby_id + "_")
            log.debug("All images downloaded for %s", colby_id)
        log.info("Image retrieval completed.")


class StudentCollate(object):
    """ Collate a student's work and writeup into the top-level Collated directory. """
    def __init__(self, colby_id, project, writeup_urls, collated_out_dir):
        self.colby_id = colby_id
        self.project = project
        self.writeup_urls = writeup_urls
        self.stu_dir = os.path.join(CS151_MOUNT_POINT, self.colby_id)
        self.private_dir = os.path.join(self.stu_dir, "private")
        self.collated_out_dir = collated_out_dir

        self.warn_msgs = set()
        self.proj_dir = self._get_proj_dir()

        if not self.writeup_urls:
            self.warn(AbsentWriteup("No writeup labeled '%s'" % self.project.wiki_label))

    def collect(self):
        """ Collect the student's code and save the writeup. """
        self._copy_code()
        for i, writeup_url in enumerate(self.writeup_urls):
            save_writeup(writeup_url, self.collated_dest, i)

    def _copy_code(self):
        """ Copy student's code into the collated directory. """
        collated_dest = self.collated_dest

        if self.proj_dir:
            try:
                shutil.copytree(self.proj_dir, collated_dest)
            except:  # there can be issues copying between filesystems
                if os.name == "posix" or os.name == "mac":
                    subprocess.check_call(["cp", "-r", self.proj_dir,
                                           collated_dest])
                else:
                    raise
        else:
            os.mkdir(collated_dest)

    def warn(self, warning):
        """ Log a warning about the project; will ultimately go in dirname. """
        warn_text = "Warning for %s:" % self.colby_id
        if isinstance(warning, ProjectWarning):
            warn_text += " %s | %s" % (warning, warning.__doc__)
            self.warn_msgs.add(warning.label)
        log.warn(warn_text)

    @property
    def collated_dest(self):
        """ Labeled directory name (has Colby ID, identifies any errors). """
        if self.warn_msgs:
            # Sorting needed to maintain determinism with respect to warnings
            out_prefix = "AA_" + "-".join(sorted(self.warn_msgs)) + "_"
        else:
            out_prefix = ""

        # Check that we haven't previously used a different directory name
        if hasattr(self, "_old_prefix") and out_prefix != self._old_prefix:
            log.warning("Previously used a different directory for %s",
                        self.colby_id, )
        self._old_prefix = out_prefix  # Save for checking in case called again

        return os.path.join(self.collated_out_dir, out_prefix + self.colby_id)

    def _get_proj_dir(self):
        """ Return directory in which project resides (None if not found). """
        try:
            project_dir = self._find_proj_dir()
        except MultipleProjects as e:
            log.warn(e.message)
            log.error("Manually resolve which project directory applies")
            raise  # Manually resolve, run again (TODO: interactively choose?)
        except ProjectWarning as e:
            self.warn(e)
        else:
            return project_dir

    def _find_proj_dir(self):
        """ Return a directory where code is unambiguously published.

        First checks the top directory, then the private version.
        """
        matching_dirs = self._get_matching_dirs(self.stu_dir)
        if not matching_dirs:
            raise AbsentProject("No project matches regex.")
        elif len(matching_dirs) > 1:
            raise MultipleProjects("Ambiguous which is project: %s" % matching_dirs)
        else:
            proj_dir = matching_dirs[0]
            if os.path.dirname(proj_dir) != self.stu_dir:
                log.debug("No top-level project found for '%s', "
                          "using '%s'", self.colby_id, proj_dir)
            return proj_dir

    def _get_matching_dirs(self, search_dir):
        """ Return absolute paths to directories that likely contain the project.

        At the first top-down directory to contain one or more matching
        directories, it returns all such matching directories. If no levels
        contain a matching directory, an empty list is returned.

        With the below directories, ['/foo/proj2', '/foo/project_2'] is returned:

            /foo
                proj2/
                project_2/
                    proj_2_again/
                    lab_2/
        """
        for (dirpath, dirnames, _) in os.walk(search_dir):
            cur_dirpaths = [os.path.join(dirpath, name) for name in dirnames]
            matching_dirs = [d for d in cur_dirpaths if self.project.match(d)]
            if matching_dirs:
                return map(os.path.abspath, matching_dirs)
        else:
            return []


def make_proj_regex(proj_num):
    """ Return a regex that permissively matches possible project dirnames. """
    numbers = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
               7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven"}
    try:
        en_num = numbers[proj_num]
    except KeyError:
        en_num = proj_num
    regex_string = ".*(lab|proj(ect)?)[-_\s]*(0*%d|%s)" % (proj_num, en_num)
    return re.compile(regex_string, re.IGNORECASE)


def save_writeup(writeup_url, dest_dir, number=False):
    """ Save the writeup to its destination directory.

    :param writeup_url: URL to a writeup ("http://.../display/~colby_id/...")
    :param dest_dir: Directory to save the PDF to
    :param number: An optional number indicating it's the nth writeup file
    """
    pdf_name = "writeup%s.pdf" % ("" if not number else number)
    dest_pdf = os.path.join(dest_dir, pdf_name)

    # Create a URL that logs in, and redirects to the desired page
    # (simplest way to log in; wkhtmltopdf and rasterize handle it)
    # NOTE: Ideally, we should be able to use the cookie that
    # mechanize maintains, but I couldn't get it working
    os_destination = writeup_url[writeup_url.find('/display/'):]
    params = urllib.urlencode({"os_username": OS_USERNAME,
                               "os_password": OS_PASSWORD,
                               "os_destination": os_destination})
    redirect_url = 'https://wiki.colby.edu/login.action?%s' % params

    if "wkhtmltopdf" in PDF_PRINTER.lower():
        cmd = [PDF_PRINTER, redirect_url, dest_pdf]
        subprocess.check_call(cmd + ["--quiet"] if not VERBOSE else cmd)
    elif "phantomjs" in PDF_PRINTER.lower():
        subprocess.check_call([PDF_PRINTER, "rasterize.js", redirect_url,
                               dest_pdf, "Letter"])
    else:
        raise ValueError("No valid PDF printer detected in %s.\n"
                         "Supported printers are wkhtmltopdf or PhantomJS\n"
                         "(is 'phantomjs'/'wkhtmltopdf' not in the path? .\n"
                         % PDF_PRINTER)

    return dest_pdf


def collate(proj_num, students_fn):
    """ Run collation on a single CS project.

    :param proj_num: An integer denoting the project number
    :param students_fn: A file with a student ID on each line
    """
    if BACKUP_CS_151:
        log.info("Backing up before doing anything")
        backup_name = "151_backup_%s" % datetime.datetime.now()
        log.info("Copying '%s' to '%s'", CS151_MOUNT_POINT, backup_name)
        shutil.copytree(CS151_MOUNT_POINT, backup_name)
        log.info("Backup completed")

    coll = Collate(proj_num)
    with open(students_fn) as students_list:
        students = [line.strip() for line in students_list]

    coll.save_all_images(students)
    coll.collate_projects(students)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Collate a project')
    parser.add_argument('proj_num', type=int,
                        help='The number of the CS151 project')
    parser.add_argument('students_file',
                        help="A text file with a Colby ID per line")
    parser.add_argument('-v', '--verbose', action="store_true",
                        help="Print extra information")
    parser.add_argument('--backup', action="store_true",
                        help="Backup %s before collation" % CS151_MOUNT_POINT)

    args = parser.parse_args()
    if not OS_USERNAME:
        OS_USERNAME = raw_input("Colby username: ")
    OS_PASSWORD = getpass.getpass("Colby password: ")
    VERBOSE = args.verbose
    if VERBOSE:
        stdout_info.setLevel(logging.DEBUG)

    BACKUP_CS_151 = args.backup

    collate(args.proj_num, args.students_file)
