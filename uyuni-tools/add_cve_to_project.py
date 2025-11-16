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
import sys
import time
from argparse import RawTextHelpFormatter

import smtools


def get_project_source_labels(project):
    """
    Retrieve the source channel labels for a given project.

    This function fetches all source entries associated with the specified
    project and extracts their channel labels into a list. The process
    includes logging debug start and finish messages.

    :param project: The project for which source channel labels are
        to be retrieved
    :type project: str
    :return: A list of channel labels extracted from the project sources
    :rtype: list
    """
    smt.log_debug("Start get_project_source_labels")
    project_sources = smt.contentmanagement_listprojectsources(project)
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


def add_cve_channels(project, env, cve):
    """
    Adds CVE (Common Vulnerabilities and Exposures) to the appropriate software channels.

    This function determines which channels should include the given CVE by analyzing the project's source
    labels and advisory channels. It either skips channels where the CVE is already present or clones
    CVE-related information and adds the necessary packages to the respective channels. It also regenerates
    the YUM cache for updated channels.

    :param project: The project identifier or name to fetch source labels.
    :type project: str
    :param env: The environment name (e.g., production, staging) to distinguish channels.
    :type env: str
    :param cve: The identifier for the Common Vulnerability and Exposure to be added to channels.
    :type cve: str
    :return: None
    """
    smt.log_debug("Start add_cve_channels")
    project_channels = get_project_source_labels(project)
    advisory_channels = get_advisory_channels(cve)
    for project_channel in project_channels:
            channel_to_clone = f"{project}-{env}-{project_channel}"
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
                smt.channel_software_regenerateyumcache(channel_to_clone)
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
        add_cve_channels(project_info.get('label'), project_info.get('firstEnvironment'), cve)
    smt.log_debug("Finished do_add_cves")

def perform_update(project, cves):
    """
    Performs an update on the given project by retrieving its environment details
    and adding CVE channels to each environment.

    This function processes the project's environments and adds the given list of
    CVE channels to each identified environment. Debug logs are generated at the
    start and at the completion of the operation.

    :param project: The name or identifier of the project to update.
    :type project: str
    :param cves: A list of CVEs to be added to the project's environments.
    :type cves: list
    :return: None
    """
    smt.log_debug("Start perform_update")
    project_details = smt.contentmanagement_listprojectenvironment(project)
    for environment_details in project_details:
        env = environment_details.get('label')
        for cve in cves:
            add_cve_channels(project, env, cve)
    smt.log_debug("Finished perform_update")

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
                promote_environment(project, source_env, target_env)
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

def promote_environment(project, source_env, target_env):
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
    if args.promote and args.update:
        smt.log_error(f"The options --promote and --update can not be used together. Aborting operation")
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
    This script adds a CVE to the first stage of a specified project. It provides options
    to update or promote other environments of the project. It uses the SMTools to manage
    and log activities.

    :raises argparse.ArgumentError: If required arguments are not provided.

    :param -p --project: The name of the project where the CVE will be added.
    :param -c --cve: The CVE Number(s). This option can be used multiple times.
    :param -u --update: A flag to update all other environments of the project.
    :param -p --promote: A flag to promote all other environments of the project.
    :param --version: Displays the version of the script.
    :type -p --project: str
    :type -c --cve: list of str
    :type -u --update: bool
    :type -p --promote: bool

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
    parser.add_argument("-r", "--promote", action="store_true", default=0,
                        help="Promote all other environments of the project")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0, November 7, 2025')
    args = parser.parse_args()
    smt.log_info("Start")
    smt.log_debug("Given options: {}".format(args))
    smt.suman_login()
    project_info, cves = check_arguments(args)
    smt.log_info(f"Project {project_info}")
    smt.log_info(f"Add CVEs: {cves}")
    if args.update:
        perform_update(args.project, cves)
    else:
        do_add_cves(project_info, cves)
    if args.promote:
        perform_promote(args.project)
    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())