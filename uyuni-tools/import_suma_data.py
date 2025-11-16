#!/usr/bin/env python3
#
# (c) 2025 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support
# For question/suggestions/bugs mail: michael.brookhuis@suse.com
#
# Version: 2025-11-14
#
# Created by: SUSE Michael Brookhuis
#
# This script will import data from a file to mlm.
#
# Releases:
# 2025-11-14 M.Brookhuis - initial release.
#

import argparse
import sys

import smtools


def process_group(input_file):
    try:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        smt.fatal_error(f"Error: Input file not found at {input_file}")
        return

    name = description = ""
    for line in lines:
        line = line.strip()
        if line.startswith("Name"):
            name = line.split(":")[1].strip()
        if line.startswith("Description"):
            description = line.split(":")[1].strip()
        if name and description:
            smt.systemgroup_create(name, description, False)
            name = description = ""


def parse_arguments(args):
    """
    Parses command-line arguments using argparse.
    group, user, and repo are mutually exclusive, and one is required.
    an inputfile is also required.
    """
    parser = argparse.ArgumentParser(
        description="This script will import data from a file to mlm. Valid options are user, repo, group."
    )

    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0, November 14, 2025')

    # 1. Add the required inputfile argument
    parser.add_argument(
        '-f', '--file', type=str, required=True,
        help='The required input file path.'
    )

    group_type = parser.add_mutually_exclusive_group(required=True)
    group_type.add_argument(
        '-g', '--group', action='store_true', default=False,
        help='Operate on a group. Create input file with:'
             '\n for x in $(spacecmd -q -- group_list);do spacecmd -q -- group_details $x;echo;done > groups.txt'
             '\n(mutually exclusive with --user and --repo).')
    group_type.add_argument(
        '-u', '--user', action='store_true', default=False,
        help='Operate on a user. Create input file with:'
             '\n for x in $(spacecmd -q -- user_list);do spacecmd -q -- user_details $x;echo;done > users.txt'
             '\n(mutually exclusive with --user and --repo).')
    group_type.add_argument(
         '-r', '--repo', action='store_true', default=False,
        help='Operate on a repository. Create input file with:'
             '\n for x in $(spacecmd -q -- repo_list);do spacecmd -q -- repo_details $x;echo;done > repos.txt'
             '\n(mutually exclusive with --user and --group).')

    return parser.parse_args(args)

# Example usage:
if __name__ == '__main__':
    # Parse the arguments
    global smt
    smt = smtools.SMTools("import_suma_data")
    smt.log_info("Start")

    smt.suman_login()
    try:
        args = parse_arguments(sys.argv[1:])
        smt.log_debug("Given options: {}".format(args))
        if args.group:
            process_group(args.file)
        elif args.user:
            print("Operation Type: User")
        elif args.repo:
            print("Operation Type: Repo")
    except SystemExit as e:
        if e.code != 0:
            print("\nError encountered.")
    smt.log_info("Finished manage_group")
    smt.close_program()
