#!/usr/bin/env python
# David Cain
# 2013-02-08

""" A script to automatically collate projects for CS151 students.

Dependencies: wkhtmltopdf (for automated printing of writeups)
"""

import os
import re
import shutil
import subprocess


SEMESTER, YEAR = "s", 13  # s for spring, f for fall
CS151_MOUNT_POINT = "/mnt/CS151"
COLLATED_DIR = "/mnt/CS151/Collated/"
PROJ_REGEX = "^proj(ect)?[_\s]*0*%d$"  # substitute project number


class AbsentWriteup(Exception):
    pass


class AbsentProject(Exception):
    pass


class Project(object):
    def __init__(self, proj_num):
        self.proj_regex = re.compile(PROJ_REGEX % proj_num, re.IGNORECASE)
        self.wiki_label = "cs151%s%dproject%d" % (SEMESTER, YEAR, proj_num)
        self.proj_num = proj_num

    def match(self, dirname):
        return self.proj_regex.match(os.path.split(dirname)[1])


class Collate(object):
    def __init__(self, proj_num):
        self.project = Project(proj_num)
        self.collated_proj_dir = os.path.join(COLLATED_DIR,
                                              "Proj%d" % proj_num)
        self.reset_collated_dir()

    def reset_collated_dir(self):
        if os.path.isdir(self.collated_proj_dir):
            shutil.rmtree(self.collated_proj_dir)
        os.mkdir(self.collated_proj_dir)

    def collate_projects(self, students):
        for colby_id in students:
            stu = StudentCollate(colby_id, self.project, self.collated_proj_dir)
            stu.collect()
            stu.get_writeup(None)


class StudentCollate(object):
    def __init__(self, colby_id, project, collated_out_dir):
        self.colby_id = colby_id
        self.project = project
        self.stu_dir = os.path.join(CS151_MOUNT_POINT, self.colby_id)
        self.private_dir = os.path.join(self.stu_dir, "private")
        self.collated_dest = os.path.join(collated_out_dir, self.colby_id)

    def collect(self):
        """ Collect student's code into the collated directory. """
        if os.path.isdir(self.collated_dest):
            print "Removing existing directory '%s'" % self.collated_dest
            shutil.rmtree(self.collated_dest)

        try:
            proj_dir = self.get_proj_dir()
        except ValueError as e:
            print e.message
            # TODO: resolve interactivity?
            print "Resolve which project directory applies"
            raise

        shutil.copytree(proj_dir, self.collated_dest)

    def get_proj_dir(self):
        """ Return a directory where code in unambiguously published.

        Will try to publish private version if possible.
        """
        # Find all matching directories in top level, then private if need be
        matching_dirs = self._get_matching_dirs(self.stu_dir)
        if not matching_dirs:
            matching_dirs = self._get_matching_dirs(self.private_dir)
            if not matching_dirs:
                raise AbsentProject("No project found for '%s'." % self.colby_id)
            if len(matching_dirs) == 1:
                print "No published project for '%s', using private version." % self.colby_id

        if len(matching_dirs) > 1:
            raise ValueError("Ambiguous which is project: %s" % matching_dirs)
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

    def get_writeup(self, writeup_url):
        print self.project.wiki_label
        dest_pdf = os.path.join(self.collated_dest, "writeup.pdf")
        subprocess.check_call(["wkhtmltopdf", "--quiet", writeup_url, dest_pdf])
        return dest_pdf
