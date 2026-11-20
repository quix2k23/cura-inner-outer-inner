#!/usr/bin/env python3
"""Checks that every -o option given to Conan really took effect.

    check-conan-options.py <conan graph info --format=json output> <the same arguments that were passed to Conan>...

Conan ignores an option whose package pattern matches nothing, without any warning (for example when quote characters
end up inside the pattern). This fails if a "-o pattern:key=value" matches no package in the graph, or if a package it
matches resolved the option to a different value. An option without a pattern ("-o key=value") applies to the package
being built.
"""
import fnmatch
import json
import sys


def requested_options(args):
    options = []
    for i, arg in enumerate(args):
        if arg in ("-o", "--options", "-o:h", "--options:host") and i + 1 < len(args):
            options.append(args[i + 1])
        elif arg.startswith(("-o=", "--options=")):
            options.append(arg.split("=", 1)[1])
    return options


def main():
    with open(sys.argv[1]) as f:
        graph = json.load(f)["graph"]["nodes"]
    consumer = graph["0"]
    # "-o" sets host options; packages that are also tools in the build context keep their own defaults.
    nodes = [n for n in graph.values() if n.get("context", "host") == "host"]
    ok = True
    for option in requested_options(sys.argv[2:]):
        head, _, value = option.partition("=")
        pattern, _, key = head.rpartition(":")
        if pattern:
            matched = [n for n in nodes if n.get("ref") and fnmatch.fnmatchcase(n["ref"].split("#")[0], pattern)]
        else:
            matched = [consumer]
        if not matched:
            print("error: option %r matches no package in the graph, so Conan ignored it" % option)
            ok = False
            continue
        for node in matched:
            actual = (node.get("options") or {}).get(key)
            name = node.get("ref") or node.get("label") or "the consumer"
            if str(actual) != value:
                print("error: option %r: %s has %s=%s" % (option, name, key, actual))
                ok = False
            else:
                print("ok: %s has %s=%s" % (name, key, actual))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
