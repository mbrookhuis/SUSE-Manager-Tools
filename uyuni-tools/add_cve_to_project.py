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
import datetime
import sys
import time
from argparse import RawTextHelpFormatter

import smtools

def get_project_source_labels(project_info):
    """
    Fetch and return the list of channel labels for the given project's sources.

    This function interacts with a content management system to retrieve the
    sources associated with the specified project. It extracts and compiles
    the labels of all channels linked to the project's sources.

    :param project_info: A dictionary containing information about the project,
        including its name.
    :type project_info: dict
    :return: A list of channel labels retrieved from the project's sources.
    :rtype: list
    """
    smt.log_debug("Start get_project_source_labels")
    project_sources = smt.contentmanagement_listprojectsources(project_info.get('name'))
    channels = []
    for source in project_sources:
        channels.append(source.get('channelLabel'))
    smt.log_debug("Finished get_project_source_labels")
    return channels

def get_advisory_channels(cve):
    """
    Retrieve advisory channels for a given CVE.

    This function fetches the advisory channels linked to the provided CVE
    identifier and extracts their corresponding labels. It ensures that
    only the relevant labels are included in the result.

    :param cve: The CVE identifier for which advisory channels are to be retrieved.
    :type cve: str
    :return: A list of channel labels applicable to the provided CVE.
    :rtype: list
    """
    smt.log_debug("Start get_advisory_channels")
    adv_channels = smt.errata_applicabletochannels(cve, False)
    channels = []
    for source in adv_channels:
        channels.append(source.get('label'))
    smt.log_debug("Finished get_advisory_channels")
    return channels

def get_cve_packages(cve):
    """
    Retrieve the list of package IDs associated with a specific CVE.

    This function fetches a list of packages related to a given CVE by querying
    the `smt.errata_listpackages` function. It then processes the result to
    extract and return only the package IDs.

    :param cve: The Common Vulnerabilities and Exposures (CVE) ID for which
        associated package IDs are to be retrieved.
    :type cve: str
    :return: A list of package IDs associated with the provided CVE.
    :rtype: list
    """
    smt.log_debug("Start get_cve_packages")
    cve_packages = smt.errata_listpackages(cve)
    packages = []
    for cve_package in cve_packages:
        packages.append(cve_package.get('id'))
    smt.log_debug("Finished get_cve_packages")
    return packages


def add_cve_channels(project_info, cve):
    """
    Adds a CVE to appropriate project channels by evaluating and cloning relevant advisory channels.

    This function determines which project channels are associated with the given CVE and ensures
    that the CVE is incorporated into the appropriate channels. If a channel already contains the
    specific CVE, no further action is taken for that channel. Otherwise, the CVE is cloned into
    the necessary channels and associated packages are added.

    :param project_info: Dictionary containing details about the project, including its name
        and environment. Used to determine the project channels.
    :type project_info: dict
    :param cve: The CVE identifier to be processed and added to needed project channels.
    :type cve: str
    :return: None
    """
    smt.log_debug("Start add_cve_channels")
    project_channels = get_project_source_labels(project_info)
    advisory_channels = get_advisory_channels(cve)
    for project_channel in project_channels:
            channel_to_clone = f"{project_info.get('name')}-{project_info.get('firstEnvironment')}-{project_channel}"
            if channel_to_clone in advisory_channels:
                smt.log_info(f"CVE is already in channel {channel_to_clone}")
                continue
            if project_channel in advisory_channels:
                cves= [cve]
                results = smt.errata_clone(channel_to_clone, cves)
                for result in results:
                    packages = get_cve_packages(result.get('advisory_name'))
                    smt.channel_software_addpackages(channel_to_clone, packages)
                    smt.log_debug(f"packages: {packages}")
                smt.log_info(f"CVE added to channel {channel_to_clone}")
    smt.log_debug("Finished add_cve_channels")

def do_add_cves(project_info, cves):
    """
    Executes the addition of CVE (Common Vulnerabilities and Exposures) entries to the
    specified project by calling the necessary routines for each CVE in the provided list.
    Logs the start and end of the operation for debugging purposes.

    :param project_info: Contains information about the project to which the CVEs will be
        added.
    :type project_info: dict
    :param cves: List of CVE identifiers to be processed and added to the specified
        project.
    :type cves: list
    :return: None
    """
    smt.log_debug("Start do_add_cves")
    for cve in cves:
        add_cve_channels(project_info, cve)
    smt.log_debug("Finished do_add_cves")


def perform_promote(project):
    """
    Perform a promotion operation within a content management system for the provided project. The function iterates
    through the project environments, identifies the source environment, and performs an update operation to promote
    changes from the source environment to the target environment.

    :param project: The project identifier or object being promoted, used to retrieve and process environment
                    details.
    :type project: Any
    :return: None
    """
    smt.log_debug("Start perform_promote")
    project_details = smt.contentmanagement_listprojectenvironment(project)
    for environment_details in project_details:
        try:
            source_env = environment_details.get('previousEnvironmentLabel')
        except KeyError:
            continue
        else:
            if source_env:
                target_env = environment_details.get('label')
                update_environment(project, source_env, target_env)
    smt.log_debug("Finished perform_promote")

def sync_completed(env, project, wait):
    """
    Checks the synchronization status of a specified project environment and waits if directed.

    This function continuously checks the status of a given environment within a project until
    it determines that the synchronization process is complete. If the environment is in a "building"
    or "generating_repodata" state, and the wait parameter is True, the function will periodically
    check the environment's status. It returns True if the environment is successfully built, or
    returns False if the environment has never been built, failed to build, or is still building
    and the wait parameter is False.

    :param env: The label of the environment to be checked.
    :type env: str
    :param project: The identifier or name of the project the environment belongs to.
    :type project: str
    :param wait: A boolean flag to specify whether to wait (with periodic checks) if the environment
                 is still in progress ("building" or "generating_repodata").
    :type wait: bool
    :return: Returns True if the environment is successfully built; False otherwise.
    :rtype: bool
    """
    smt.log_debug("Start sync_completed")
    while True:
        project_details = smt.contentmanagement_listprojectenvironment(project)
        for environment_details in project_details:
            if environment_details.get('label') == env:
                if environment_details.get('status') == "built":
                    return True
                if environment_details.get('status') == "unknown":
                    smt.log_error(f"environment {env} has never been build. Please build first")
                    return False
                if environment_details.get('status') == "failed":
                    smt.log_error(f"environment {env} failed to build. Please check logs")
                    return False
                if (environment_details.get('status') == "building" or environment_details.get('status') == "generating_repodata") and wait:
                    smt.log_debug(f"environment {env} still being build. Waiting")
                    time.sleep(30)
                else:
                    smt.log_error(f"for environment {env} building is still in progress and option wait is False.")
                    return False

def update_environment(project, source_env, target_env):
    """
    Updates the environment by promoting the project from a source environment to a
    target environment if the source environment is synchronized successfully. Logs
    debug messages at the beginning and end of the operation. Handles fatal errors
    if synchronization is not ready.

    :param project: The project name being updated
    :type project: str
    :param source_env: The source environment from which the project is promoted
    :type source_env: str
    :param target_env: The target environment to which the project is promoted
    :type target_env: str
    :return: None
    """
    smt.log_debug("Start update_environment")
    smt.log_info(f"promoting project {project} from {source_env} to {target_env}")
    smt.contentmanagement_promoteproject(project, source_env)
    sync_completed(target_env, project, True)
    smt.log_debug("Finished update_environment")

def check_arguments(args):
    """
    Checks the provided arguments for validity, including the existence of the project
    and associated CVEs (Common Vulnerabilities and Exposures).

    The function verifies:
    1. If the specified project exists.
    2. If each provided CVE is associated with valid information.

    If a project is not found or no valid CVEs are provided, the function terminates
    the execution with a logged error.

    :param args: The input arguments containing the project name and the list of CVEs.
    :type args: Namespace
    :return: A tuple containing the project information and a list of valid CVEs if all
             are valid; otherwise, terminates execution with an error.
    :rtype: Tuple[Any, List[Any]]
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
        cve_infos = smt.errata_findbycve(cve,False)
        if cve_infos:
            for cve_info in cve_infos:
                cves.append(cve_info.get("advisory_name"))
        else:
            smt.log_warning(f"CVE {cve} doesn't exists. Skipping")
    if cves:
        smt.log_debug("Finished check_arguments")
        return project_present, cves
    else:
        smt.log_error(f"No valid CVEs found. Aborting operation")
        sys.exit(1)

def main():
    """
    Main function to add a CVE to the first stage of a project or update all other environments
    of the project as specified. The script interacts with the `SMTools` library to log in,
    validate arguments, handle operations, and manage the lifecycle of CVE additions.

    The function is designed to:
    1. Parse arguments provided through the command line including project name, CVE numbers,
       and an optional update flag.
    2. Log relevant information and operations throughout the process.
    3. Execute the specified CVE addition task or optional update of all environments.
    4. Properly terminate operations and close the program.

    :param args: Command-line arguments for project name, CVEs to add, and an optional update flag.
    :type args: argparse.Namespace

    :raises:
        `SystemExit` if required arguments are missing or invalid during argument parsing.

    :return: None
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
    do_add_cves(project_info, cves)
    if args.update:
        perform_promote(args.project)
    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())