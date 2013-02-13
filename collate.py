#!/usr/bin/env python
# David Cain
# 2013-02-12

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
PROJ_REGEX = ".*(lab|proj(ect)?)[_\s]*0*%d$"  # substitute project number


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

    def warn(self, warning):
        if isinstance(warning, ProjectWarning):
            #print warning.__doc__
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
            # TODO: resolve interactivity?
            print "Resolve which project directory applies"
            raise
        except ProjectWarning as e:
            self.warn(e)

        collated_dest = self._get_dest_dirname()
        if not self.writeup_urls:
            self.warn(AbsentWriteup("Can't find writeup for '%s'" % self.colby_id))
            collated_dest = self._get_dest_dirname()  # New dirname includes error
        else:
            for i, writeup_url in enumerate(self.writeup_urls):
                save_writeup(writeup_url, collated_dest, i)

        if proj_dir:
            shutil.copytree(proj_dir, collated_dest)
        else:
            os.makedirs(collated_dest)

    def _get_dest_dirname(self):
        if self.warn_msgs:
            out_prefix = "AA_" + "-".join(sorted(self.warn_msgs)) + "_"
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
    pdf_name = "writeup%s.pdf" % ("" if not number else number)
    dest_pdf = os.path.join(dest_dir, pdf_name)
    #subprocess.check_call(["wkhtmltopdf", "--quiet", writeup_url, dest_pdf])
    print " ".join(["wkhtmltopdf",  writeup_url, dest_pdf])
    subprocess.check_call(["wkhtmltopdf",  writeup_url, dest_pdf])
    #p = writeups.PageFetch("cs151s13project1")
    return dest_pdf


if __name__ == "__main__":
    project = Project(1)
    coll = Collate(1)
    with open("students.txt") as students_list:
        students = [line.strip() for line in students_list]

    coll.collate_projects(students)
