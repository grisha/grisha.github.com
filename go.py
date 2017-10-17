
import os

lines = open("LOG").readlines()

for line in lines:
    cmd = "git merge %s" % line.split()[0]
    print cmd
    os.system(cmd)
