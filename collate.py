#!/usr/bin/env python
# David Cain
# 2013-02-13

""" A script to automatically collate projects for CS151 students.

Dependencies: wkhtmltopdf or phantomjs (for automated printing of writeups)
"""

import datetime
import getpass
import os
import re
import shutil
import subprocess
import urllib

import writeups


SEMESTER, YEAR = "s", 13  # s for spring, f for fall
CS151_MOUNT_POINT = "/mnt/CS151"
BACKUP_CS_151 = True
COLLATED_DIR = "/mnt/CS151/Collated/"

# Needs to be read here, because we can't use cookie with wkhtmltopdf/rasterize
OS_USERNAME = "djcain"
OS_PASSWORD = getpass.getpass()

PDF_PRINTER = "wkhtmltopdf"  # (or phantomjs)


def make_proj_regex(proj_num):
    numbers = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
               7: "seven", 8: "eight", 9: "nine", 10: "ten"}
    try:
        en_num = numbers[proj_num]
    except KeyError:
        en_num = proj_num
    regex_string = ".*(lab|proj(ect)?)[_\s]*(0*%d|%s)" % (proj_num, en_num)
    return re.compile(regex_string, re.IGNORECASE)


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


class PrivateProject(ProjectWarning):
    """No published project was found, using a version found in 'private'."""
    label = "PRIVATE_VERSION"


class Project(object):
    """ Store attributes about a single CS151 project. """
    def __init__(self, proj_num):
        self.proj_regex = make_proj_regex(proj_num)
        self.wiki_label = "cs151%s%dproject%d" % (SEMESTER, YEAR, proj_num)
        self.proj_num = proj_num

    def match(self, dirname):
        return self.proj_regex.match(os.path.split(dirname)[1])


class Collate(object):
    """ Collate all students' work for a given project. """
    def __init__(self, proj_num):
        self.project = Project(proj_num)
        writeup_urls = writeups.get_writeups(self.project.wiki_label)
        self.writeups_dict = writeups.writeup_by_id(writeup_urls)
        self.collated_proj_dir = os.path.join(COLLATED_DIR, "Proj%d" % proj_num)
        self.reset_collated_dir()

    def reset_collated_dir(self):
        """ Create a fresh directory to store the collated projects. """
        if os.path.isdir(self.collated_proj_dir):
            print "About to delete '%s'" % self.collated_proj_dir
            print "Press Enter to continue, Ctrl+C to abort"
            raw_input()
            shutil.rmtree(self.collated_proj_dir)
        os.mkdir(self.collated_proj_dir)

    def collate_projects(self, students):
        for colby_id in students:
            try:
                writeup_urls = self.writeups_dict[colby_id]
            except KeyError:
                writeup_urls = []

            stu = StudentCollate(colby_id, self.project, writeup_urls,
                                 self.collated_proj_dir)
            stu.collect()


class StudentCollate(object):
    """ Collate a student's work and writeup into the top-level Collated directory. """
    def __init__(self, colby_id, project, writeup_urls, collated_out_dir):
        self.colby_id = colby_id
        self.project = project
        self.writeup_urls = writeup_urls
        self.stu_dir = os.path.join(CS151_MOUNT_POINT, self.colby_id)
        self.private_dir = os.path.join(self.stu_dir, "private")
        self.collated_out_dir = collated_out_dir

        self.warn_msgs = []

    def warn(self, warning, verbose=False):
        """Log a warning about the project; will ultimately go in directory name. """
        if verbose:
            print "Warning for '%s':" % self.colby_id,
        if isinstance(warning, ProjectWarning):
            if verbose:
                print warning, "|", warning.__doc__
            warning = warning.label

        if warning not in self.warn_msgs:
            self.warn_msgs.append(warning)

    def collect(self):
        """ Collect student's code into the collated directory. """
        proj_dir = None
        try:
            proj_dir = self._get_proj_dir()
        except MultipleProjects as e:
            print e.message
            print "Resolve which project directory applies"
            raise  # Manually resolve, run again (TODO: interactively choose?)
        except ProjectWarning as e:
            self.warn(e)

        if not self.writeup_urls:
            self.warn(AbsentWriteup("Can't find writeup for '%s'" % self.colby_id))

        # Dirname should include all proper errors now
        collated_dest = self._get_dest_dirname()

        if proj_dir:
            shutil.copytree(proj_dir, collated_dest)
        else:
            os.mkdir(collated_dest)

        for i, writeup_url in enumerate(self.writeup_urls):
            save_writeup(writeup_url, collated_dest, i)

    def _get_dest_dirname(self):
        """ Return the labeled directory name (identifies any errors). """
        if self.warn_msgs:
            out_prefix = "AA_" + "-".join(sorted(self.warn_msgs)) + "_"
        else:
            out_prefix = ""
        return os.path.join(self.collated_out_dir, out_prefix + self.colby_id)

    def _get_proj_dir(self):
        """ Return a directory where code in unambiguously published.

        First checks the top directory, then the private version.
        """
        # Find all matching directories in top level, then private if need be
        matching_dirs = self._get_matching_dirs(self.stu_dir)
        if not matching_dirs:
            # Try for a project in the private directory
            matching_dirs = self._get_matching_dirs(self.private_dir)
            if not matching_dirs:
                raise AbsentProject("No project found for '%s'." % self.colby_id)
            elif len(matching_dirs) == 1:
                self.warn(PrivateProject(self.colby_id))

        if len(matching_dirs) > 1:
            raise MultipleProjects("Ambiguous which is project: %s" % matching_dirs)
        return matching_dirs[0]

        # Return matching directory if found, raise Exceptions if absent

    def _get_matching_dirs(self, search_dir):
        """ Search for a project in the top level of the given directory. """
        # Obtain all matching directories (hopefully, just one matches)
        init_dir = os.getcwd()
        os.chdir(search_dir)
        all_dirs = [path for path in os.listdir(search_dir) if os.path.isdir(path)]
        matching_dirs = [d for d in all_dirs if self.project.match(d)]
        abs_dirs = map(os.path.abspath, matching_dirs)
        os.chdir(init_dir)

        return abs_dirs


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
    os_destination = writeup_url[writeup_url.find('/display/'):]
    params = urllib.urlencode({"os_username": OS_USERNAME,
                               "os_password": OS_PASSWORD,
                               "os_destination": os_destination})
    redirect_url = 'https://wiki.colby.edu/login.action?%s' % params

    pdf_printer = PDF_PRINTER.lower()
    if pdf_printer == "wkhtmltopdf":
        subprocess.check_call(["wkhtmltopdf", "--quiet",  redirect_url, dest_pdf])
    elif pdf_printer == "phantomjs":
        subprocess.check_call(["phantomjs", "rasterize.js", redirect_url,
                               dest_pdf, "Letter"])
    else:
        raise ValueError("Supported PDF printers are wkhtmltopdf or PhantomJS")

    return dest_pdf


def collate(proj_num, students_fn):
    """ Run collation on a single CS project.

    :param proj_num: An integer denoting the project number
    :param students_fn: A file with a student ID on each line
    """
    if BACKUP_CS_151:
        print "Backing up before doing anything"
        backup_name = "151_backup_%s" % datetime.datetime.now()
        shutil.copytree("/mnt/CS151", backup_name)
        print "Backup done (saved to '%s')" % backup_name

    coll = Collate(proj_num)
    with open(students_fn) as students_list:
        students = [line.strip() for line in students_list]

    coll.collate_projects(students)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Collate a project')
    parser.add_argument('proj_num', type=int,
                        help='The number of the CS151 project')
    parser.add_argument('students_file',
                        help="A text file with a Colby ID per line")

    args = parser.parse_args()
    collate(args.proj_num, args.students_file)
