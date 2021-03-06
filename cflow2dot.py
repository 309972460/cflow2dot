#!/usr/bin/env python

import os.path
import sys
import subprocess
import re
import argparse
import json

from sys import exit
from os import system

cflow_path = "/usr/local/bin/cflow"
dot_path = "/usr/local/bin/dot"
color = ["#eecc80", "#ccee80", "#80ccee", "#eecc80", "#80eecc"];
shape =["box", "ellipse", "octagon", "hexagon", "diamond"];
shape_len = len(shape)
pref = "cflow"
exts = ["svg", "png"]
index = {}
count = {}

stdlib = [
"assert", "isalnum", "isalpha", "iscntrl", "isdigit", "isgraph", "islower",
"isprint", "ispunct", "isspace", "isupper", "isxdigit", "toupper", "tolower",
"errno", "setlocale", "acos", "asin", "atan", "atan2", "ceil", "cos", "cosh",
"exp", "fabs", "floor", "fmod", "frexp", "ldexp", "log", "log10", "modf",
"pow", "sin", "sinh", "sqrt", "tan", "tanh", "stdlib.h", "setjmp", "longjmp",
"signal", "raise", "clearerr", "fclose", "feof", "fflush", "fgetc", "fgetpos",
"fgets", "fopen", "fprintf", "fputc", "fputs", "fread", "freopen", "fscanf",
"fseek", "fsetpos", "ftell", "fwrite", "getc", "getchar", "gets", "perror",
"printf", "putchar", "puts", "remove", "rewind", "scanf", "setbuf", "setvbuf",
"sprintf", "sscanf", "tmpfile", "tmpnam", "ungetc", "vfprintf", "vprintf",
"vsprintf", "abort", "abs", "atexit", "atof", "atoi", "atol", "bsearch",
"calloc", "div", "exit", "getenv", "free", "labs", "ldiv", "malloc", "mblen",
"mbstowcs", "mbtowc", "qsort", "rand", "realloc", "strtod", "strtol",
"strtoul", "srand", "system", "wctomb", "wcstombs", "memchr", "memcmp",
"memcpy", "memmove", "memset", "strcat", "strchr", "strcmp", "strcoll",
"strcpy", "strcspn", "strerror", "strlen", "strncat", "strncmp", "strncpy",
"strpbrk", "strrchr", "strspn", "strstr", "strtok", "strxfrm", "asctime",
"clock", "ctime", "difftime", "gmtime", "localtime", "mktime", "strftime",
"time","vsnprintf"]

pthreadlib = [
"pthread_atfork", "pthread_attr_destroy", "pthread_attr_getdetachstate",
"pthread_attr_getguardsize", "pthread_attr_getinheritsched",
"pthread_attr_getschedparam", "pthread_attr_getschedpolicy",
"pthread_attr_getscope", "pthread_attr_getstack", "pthread_attr_getstackaddr",
"pthread_attr_getstacksize", "pthread_attr_init",
"pthread_attr_setdetachstate", "pthread_attr_setguardsize",
"pthread_attr_setinheritsched", "pthread_attr_setschedparam",
"pthread_attr_setschedpolicy", "pthread_attr_setscope",
"pthread_attr_setstack", "pthread_attr_setstackaddr",
"pthread_attr_setstacksize", "pthread_barrier_destroy", "pthread_barrier_init",
"pthread_barrier_wait", "pthread_barrierattr_destroy",
"pthread_barrierattr_getpshared", "pthread_barrierattr_init",
"pthread_barrierattr_setpshared", "pthread_cancel", "pthread_cleanup_pop",
"pthread_cleanup_push", "pthread_cond_broadcast", "pthread_cond_destroy",
"pthread_cond_init", "pthread_cond_signal", "pthread_cond_timedwait",
"pthread_cond_wait", "pthread_condattr_destroy", "pthread_condattr_getclock",
"pthread_condattr_getpshared", "pthread_condattr_init",
"pthread_condattr_setclock", "pthread_condattr_setpshared", "pthread_create",
"pthread_detach", "pthread_equal", "pthread_exit", "pthread_getconcurrency",
"pthread_getcpuclockid", "pthread_getschedparam", "pthread_getspecific",
"pthread_join", "pthread_key_create", "pthread_key_delete", "pthread_kill",
"pthread_mutex_destroy", "pthread_mutex_getprioceiling", "pthread_mutex_init",
"pthread_mutex_lock", "pthread_mutex_setprioceiling",
"pthread_mutex_timedlock", "pthread_mutex_trylock", "pthread_mutex_unlock",
"pthread_mutexattr_destroy", "pthread_mutexattr_getprioceiling",
"pthread_mutexattr_getprotocol", "pthread_mutexattr_getpshared",
"pthread_mutexattr_gettype", "pthread_mutexattr_init",
"pthread_mutexattr_setprioceiling", "pthread_mutexattr_setprotocol",
"pthread_mutexattr_setpshared", "pthread_mutexattr_settype", "pthread_once",
"pthread_rwlock_destroy", "pthread_rwlock_init", "pthread_rwlock_rdlock",
"pthread_rwlock_timedrdlock", "pthread_rwlock_timedwrlock",
"pthread_rwlock_tryrdlock", "pthread_rwlock_trywrlock",
"pthread_rwlock_unlock", "pthread_rwlock_wrlock", "pthread_rwlockattr_destroy",
"pthread_rwlockattr_getpshared", "pthread_rwlockattr_init",
"pthread_rwlockattr_setpshared", "pthread_self", "pthread_setcancelstate",
"pthread_setcanceltype", "pthread_setconcurrency", "pthread_setschedparam",
"pthread_setschedprio", "pthread_setspecific", "pthread_sigmask",
"pthread_spin_destroy", "pthread_spin_init", "pthread_spin_lock",
"pthread_spin_trylock", "pthread_spin_unlock", "pthread_testcancel",
"pthread_setaffinity_np"
]

def get_parser():
    ap = argparse.ArgumentParser(description="cflow2dot: generate call graph from C source code")
    ap.add_argument("-e", "--exclude", metavar="symbols",
                    help="exclude these symbols (comma separated values) from output")
    ap.add_argument("-m", "--main", metavar="NAME",
                    help="Assume main function to be called NAME")
    ap.add_argument("-r", "--rank", default="LR", choices=["LR", "same"],
                    help="if rank is \"LR\", graph is left to right. If rank is \"same\", graph is top to bottom. Default value is \"LR\".")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="increase verbosity level")
    ap.add_argument("--no", metavar="NAME", action="append",
                    help="exclude NAME symbol set (configured in ~/.cflowdotrc) from output")
    ap.add_argument("--no-pthreadlib", action="store_true",
                    help="exclude pthread lib symbols from output")
    ap.add_argument("--no-stdlib", action="store_true",
                    help="exclude C stdlib symbols from output")
    ap.add_argument("cflow_args", nargs=argparse.REMAINDER,
                    help="arguments that are passed to cflow")
    return ap

def call_cflow(opts):
    args = opts.cflow_args
    args.insert(0, cflow_path)
    args.insert(1, "-l")
    if opts.main:
        args.insert(1, "-m")
        args.insert(2, opts.main)

    if opts.verbose:
        print "calling cflow with args: ", args

    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    (stdout, stderr) = p.communicate()

    if stderr and not stdout:
        exit(stderr)
    return stdout


def build_excludes(opts):
    res = {}

    if opts.exclude:
        exclude_symbols = opts.exclude.split(",")
        for v in exclude_symbols:
            res[v] = True
    if opts.no_stdlib:
        for v in stdlib:
            res[v] = True
    if opts.no_pthreadlib:
        for v in pthreadlib:
            res[v] = True

    if opts.no:
        rcfile = os.path.expanduser("~") + "/.cflow2dotrc"
        print(rcfile)
        if not os.path.isfile(rcfile):
            print("no ~/.cflow2dotrc file found, --no argument is skipped")
            return res
        else:
            fp = open(rcfile)
            rcdata = json.load(fp)
            for exclude_set in opts.no:
                if rcdata.get(exclude_set):
                    for func_name in rcdata[exclude_set]:
                        res[func_name] = True
                else:
                    print("no key \"" + exclude_set + "\" specified in " + rcfile)
            fp.close()

    return res

def get_output(opts, res):
    output = []
    skip = False
    exclude_index = -1
    lines = res.split('\n')
    verbose = opts.verbose
    exclude = build_excludes(opts)

    for line in lines:
        if line == '':
            continue
        line = re.sub("\(.*$", "", line)
        line = re.sub("^\{\s*", "", line)
        line = re.sub("\}\s*", "\t", line)

        parts = line.split("\t")
        # indent level
        n = parts[0]
        # function name of callee
        f = parts[1]
        index[n] = f

        # test if callee is in exclude list
        if skip:
            # exclude all sub function calls from the excluded function. If we
            # get another callee at the same indent level, then stop skipping
            if int(n) > int(exclude_index):
                if verbose:
                    print("exclude sub function: " + f)
                continue
            else:
                skip = False
                exclude_index = -1
        if f in exclude:
            skip = True
            exclude_index = n
            if verbose:
                print("exclude function: " + f)
            continue

        if n != '0':
            s = "%s->%s" % (index[str(int(n) - 1)], f)
            if s not in count:
                output.append("node [color=\"{0}\" shape={1}];edge [color=\"{2}\"];\n{3}\n".format(color[int(n) % shape_len], shape[int(n) % shape_len], color[int(n) % shape_len], s))
                count[s] = True
        else:
            output.append("%s [shape=box];\n" % f)

    output.insert(0, "digraph G {\nnode [peripheries=2 style=\"filled,rounded\" fontname=\"Vera Sans YuanTi Mono\" color=\"%s\"];\nrankdir=%s;\nlabel=\"%s\"\n" % (color[0], opts.rank, opts.cflow_args[2]))
    output.append("}\n")
    return output


def write_output(output):
    f = open(pref + ".dot", "w")
    f.write(''.join(output))
    f.close()
    print("dot output to %s.dot" % pref)

    if os.path.isfile(dot_path):
        for ext in exts:
            system("dot -T%s %s.dot -o %s.%s" % (ext, pref, pref, ext))
            print("%s output to %s.%s" % (ext, pref, ext))
    else:
        print("'dot(GraphViz)' not installed.")


if __name__ == '__main__':
    ap = get_parser()
    opts = ap.parse_args()

    if not os.path.isfile(cflow_path):
        exit('cflow not found on: %s' % cflow_path)

    res = call_cflow(opts)
    output = get_output(opts, res)
    write_output(output)
