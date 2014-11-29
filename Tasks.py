#!/usr/bin/env python
"""
 just breaks out the processes that are run asynchronously in its own file
"""


import os, re, subprocess, sys
from rq import get_current_job


# perform the search
# this is a long running process best called asynchronously via rq
def search(cmd, basedir, tempdir, db_size):
    progressfile_path = os.path.join(tempdir, 'progress')
    progressfile = open(progressfile_path, "w+")
    fileid = os.path.basename(os.path.normpath(tempdir)).strip()
    tarname = fileid+".tar.gz"

    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               stdin=subprocess.PIPE)
    out = []
    err = []
    count = 0.0
    # process each line while running so we can get progress and monitor
    while True:
        line = process.stdout.readline()
        if not line:
            break
        sline = line.strip()
        # check for progress, don't store visiting
        if re.search('Visiting', sline):
            count += 1
            progress = str(count / float(db_size))
            progressfile.seek(0)
            progressfile.write(progress+"\n")
            progressfile.truncate()
            progressfile.flush()
        # check for error -- master returns true regardless if it hits an error...
        elif re.search('Error:', sline):
            err.append(sline)
        else:
            out.append(sline)
        sys.stdout.flush()
    err += process.stderr.readlines()  # append any stderr to stdout "Errors"
    if err:
        str_err = "\n".join(err)
        raise Exception(str_err)

    # compress the resultsdir
    compress_cmd = ['/usr/bin/tar', '-C', basedir, '-czf', os.path.join(basedir, tarname), fileid]
    compress_process = subprocess.Popen(compress_cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        stdin=subprocess.PIPE)
    c_out, c_err = compress_process.communicate()
    if c_err and not re.search('Removing', c_err):
        raise Exception(str(c_err))

    # return the fileid once all done processing
    return fileid
    # TODO: handle errors how?