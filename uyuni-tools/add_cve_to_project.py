#!/usr/bin/env python3
#
# (c) 2025 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support
# For question/suggestions/bugs mail: michael.brookhuis@suse.com
#
# Version: 2025-11-07
#
# Created by: SUSE Michael Brookhuis
#
# This script will add a CVE to the first stage of a project.
#
# Releases:
# 2025-11-07 M.Brookhuis - initial release.
#

import argparse
import base64
import datetime
import socket
import ssl
import sys
import xmlrpc.client
from argparse import RawTextHelpFormatter

import smtools


def check_arguments(args):
    """
    Check if the required arguments are passed.

    :param args:
    :return:
    """
    smt.log_debug("Start check_arguments")

    # check if project exists
    project_present = smt.contentmanagement_lookupproject(args.project)
    if not project_present:
        smt.log_error(f"Project {args.project} doesn't exists. Aborting operation")
        sys.exit(1)
    # check if CVE exists
    cves = []
    for cve in args.cve:
        cve_present = smt.errata_findbycve(cve,False)
        if not cve_present:
            smt.log_warning(f"CVE {cve} doesn't exists. Skipping")
        else:
            cves.append(cve)

    return project_present, cves



def main():
    """
    Main section
    """
    global smt
    smt = smtools.SMTools("add_cve_to_project")
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
         Usage:
         add_cve_to_project.py

         This script will add a CVE to the first stage of a project.

               '''))
    parser.add_argument("-p", "--project", help="name of project where the CVE has to be added",
                        required=True)
    parser.add_argument("-c", "--cve", action="append",
                        help="The CVE Number. This option can be used multuple times", required=True)
    parser.add_argument("-u", "--update", action="store_true", default=0,
                        help="Update all other environments of the project")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0, November 7, 2025')
    args = parser.parse_args()
    smt.log_info("Start")
    smt.log_debug("Given options: {}".format(args))
    smt.suman_login()
    project_info, cves = check_arguments(args)
    smt.log_info(f"Project {project_info}")
    smt.log_info(f"Add CVEs: {cves}")

    #start_sync(args, user, password)

    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())