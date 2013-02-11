#!/usr/bin/env python
# David Cain
# 2013-02-11

""" A script to automatically collate projects for CS151 students.

Dependencies: wkhtmltopdf (for automated printing of writeups)
"""

import os
import re
import shutil
import subprocess

import writeups


SEMESTER, YEAR = "s", 13  # s for spring, f for fall
CS151_MOUNT_POINT = "/mnt/CS151"
COLLATED_DIR = "/mnt/CS151/Collated/"
PROJ_REGEX = "proj(ect)?[_\s]*0*%d$"  # substitute project number


class AbsentWriteup(Exception):
    pass


class AbsentProject(Exception):
    pass


class Project(object):
    """ Store attributes about a single CS151 project. """
    def __init__(self, proj_num):
        self.proj_regex = re.compile(PROJ_REGEX % proj_num, re.IGNORECASE)
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
        self.collated_proj_dir = os.path.join(COLLATED_DIR,
                                              "Proj%d" % proj_num)
        self.reset_collated_dir()

    def reset_collated_dir(self):
        if os.path.isdir(self.collated_proj_dir):
            shutil.rmtree(self.collated_proj_dir)
        os.mkdir(self.collated_proj_dir)

    def collate_projects(self, students):
        for colby_id in students:
            try:
                writeup_url = self.writeups_dict[colby_id]
            except KeyError:
                writeup_url = None

            stu = StudentCollate(colby_id, self.project, writeup_url,
                                 self.collated_proj_dir)
            stu.collect()


class StudentCollate(object):
    """ Collate a student's work and writeup into the top-level Collated directory. """
    def __init__(self, colby_id, project, writeup_url, collated_out_dir):
        self.colby_id = colby_id
        self.project = project
        self.writeup_url = writeup_url
        self.stu_dir = os.path.join(CS151_MOUNT_POINT, self.colby_id)
        self.private_dir = os.path.join(self.stu_dir, "private")
        self.collated_out_dir = collated_out_dir

    def collect(self):
        """ Collect student's code into the collated directory. """
        self.warn_msgs = []
        proj_dir = None
        try:
            proj_dir = self._get_proj_dir()
        except AbsentProject:
            self.warn_msgs.append("NO_PROJECT")
        except ValueError as e:
            print e.message
            # TODO: resolve interactivity?
            print "Resolve which project directory applies"
            raise

        collated_dest = self._get_dest_dirname()
        if self.writeup_url:
            save_writeup(self.writeup_url, collated_dest)
        else:
            self.warn_msgs.append("NO_WRITEUP")
            collated_dest = self._get_dest_dirname()  # New dirname has error

        if proj_dir:
            shutil.copytree(proj_dir, collated_dest)
        else:
            os.makedirs(collated_dest)


    def _get_dest_dirname(self):
        if self.warn_msgs:
            out_prefix = "AA_" + "-".join(self.warn_msgs) + "_"
        else:
            out_prefix = ""
        return os.path.join(self.collated_out_dir, out_prefix + self.colby_id)

    def _get_proj_dir(self):
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
                self.warn_msgs.append("PRIVATE_VERSION")

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


def save_writeup(writeup_url, dest_dir):
    dest_pdf = os.path.join(dest_dir, "writeup.pdf")
    #subprocess.check_call(["wkhtmltopdf", "--quiet", writeup_url, dest_pdf])
    print " ".join(["wkhtmltopdf",  writeup_url, dest_pdf])
    subprocess.check_call(["wkhtmltopdf",  writeup_url, dest_pdf])
    return dest_pdf


if __name__ == "__main__":
    project = Project(1)
    coll = Collate(1)
