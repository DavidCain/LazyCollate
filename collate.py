import os
import re
import shutil

CS151_MOUNT_POINT = "/mnt/CS151"
COLLATED_DIR = "/mnt/CS151/Collated/"


class Collate(object):
    def __init__(self, proj_num):
        self.proj_num = proj_num
        self.proj_regex = re.compile("^proj(ect)?[_\s]*0*%d$" % proj_num, re.IGNORECASE)
        self.collated_proj_dir = os.path.join(COLLATED_DIR,
                                              "Proj%d" % self.proj_num)
        if os.path.isdir(self.collated_proj_dir):
            shutil.rmtree(self.collated_proj_dir)
        os.mkdir(self.collated_proj_dir)

    def get_proj_dir(self, colby_id):
        stu_dir = os.path.join(CS151_MOUNT_POINT, colby_id, "private")  # TODO: don't delve into private
        os.chdir(stu_dir)

        all_dirs = [path for path in os.listdir(stu_dir) if os.path.isdir(path)]
        matching_dirs = [d for d in all_dirs if self.proj_regex.match(d)]

        # Return matching directory if normal, otherwise handle cases
        if len(matching_dirs) == 1:
            return matching_dirs[0]
        elif len(matching_dirs) > 1:
            raise Exception("Ambiguous which is project: %s" % matching_dirs)
        else:
            print "No project found for '%s'." % colby_id

    def collect_student(self, colby_id):
        collated_dest = os.path.join(self.collated_proj_dir, colby_id)
        if os.path.isdir(collated_dest):
            print "Removing existing directory '%s'" % collated_dest
            shutil.rmtree(collated_dest)

        proj_dir = self.get_proj_dir(colby_id)
        if not proj_dir:
            return

        shutil.copytree(proj_dir, collated_dest)

        # TODO: Go to their wiki, print page
