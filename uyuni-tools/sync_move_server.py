#!/usr/bin/env python3
#
# (c) 2019 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support
# For question/suggestions/bugs mail: michael.brookhuis@suse.com
#
# Version: 2019-10-17
#
# Created by: SUSE Michael Brookhuis
#
# This script will clone channels from the give parent.
#
# Releasmt.session:
# 2017-01-23 M.Brookhuis - initial release.
# 2019-01-14 M.Brookhuis - Added yaml
#                        - Added logging
# 2019-02-10 M.Brookhuis - General update
# 2019-10-17 M.Brookhuis - Added support for projects and environments
# 2020-03-23 M.Brookhuis - Added backup option
# 2020-04-19 M.Brookhuis - all api calls moved to smtools.py and added debug logging
# 2025-06-06 M.Brookhuis - added check if the sync of the previous environment is completed.
#

"""
This program will sync the give stage
"""

import argparse
import base64
import binascii
import datetime
import socket
import ssl
import sys
import time
import xmlrpc.client

import smtools
from argparse import RawTextHelpFormatter

__smt = None

class smlm:
    client = ""
    session = ""
    server = ""
    systemid = ""

    def __init__(self, server, fromsmlm, user, password, skip_ssl_check):
        self.server = server
        self.fromsmlm = fromsmlm
        self.user = user
        self.password = password
        self.skip_ssl_check = skip_ssl_check
        self.login_smlm()

        self.set_hostname()

    def login_smlm(self):
        """
        Log in to SUSE Manager Server.
        """
        if not self.skip_ssl_check:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect_ex((self.fromsmlm, 443))
            except:
                smt.fatal_error(f"Unable to login to SUSE Manager server {self.fromsmlm} SOCKET")

            self.client = xmlrpc.client.Server("https://" + self.fromsmlm + "/rpc/api")
            try:
                self.session = self.client.auth.login(self.user, self.password)
            except:
                smt.fatal_error(f"Unable to login to SUSE Manager server {self.fromsmlm} XMLRPC")
        else:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect_ex((self.fromsmlm, 443))
            except:
                smt.fatal_error("Unable to login to SUSE Manager server {self.fromsmlm} SOCKET")
            context_xmlrpc = ssl.create_default_context()
            context_xmlrpc.check_hostname = False
            context_xmlrpc.verify_mode = ssl.CERT_NONE
            transport = xmlrpc.client.Transport()
            transport._ssl_wrap = lambda host, **kwargs: context_xmlrpc.wrap_socket(socket.create_connection((host, 443)), server_hostname=host)
            self.client = xmlrpc.client.Server("https://" + self.fromsmlm + "/rpc/api", transport=transport)
            try:
                self.session = self.client.auth.login(self.user, self.password)
            except:
                smt.fatal_error(f"Unable to login to SUSE Manager server {self.fromsmlm} XMLRPC")

    def set_hostname(self, fatal=True):
        """
        Set hostnam for global use.
        """
        self.get_server_id(fatal)
        smt.log_info("Hostname : {}".format(self.server))
        smt.log_info("Systemid : {}".format(self.systemid))

    def get_server_id(self, fatal=True):
        """
        Get system Id from host
        """
        hostname = self.server

        all_sid = ""
        try:
            all_sid = self.client.system.getId(self.session, hostname)
        except xmlrpc.client.Fault:
            smt.fatal_error("Unable to get systemid from system {}. Is this system registered?".format(hostname))
        system_id = 0
        for x in all_sid:
            if system_id == 0:
                system_id = x.get('id')
            else:
                if fatal:
                    smt.fatal_error("Duplicate system {}. Please fix and run again.".format(hostname))
                else:
                    smt.log_error("Duplicate system {}. Please fix and run again.".format(hostname))
                    smt.log_debug(
                        "The following system id have been found for system {}:\n{}".format(hostname, all_sid))
        if system_id == 0:
            if fatal:
                smt.fatal_error(
                    "Unable to get systemid from system {}. Is this system registered?".format(hostname))
            else:
                smt.log_error(
                    "Unable to get systemid from system {}. Is this system registered?".format(hostname))
        self.systemid = system_id
        return system_id

    def system_config_listchannels(self):
        try:
            return self.client.system.config.listChannels(self.session, self.systemid)
        except xmlrpc.client.Fault as err:
            smt.log_debug('api-call: system.config.listChannels')
            smt.log_debug('Value passed: ')
            smt.log_debug('  system_id:  {}'.format(self.systemid))
            smt.log_debug("Error: \n{}".format(err))
            smt.fatal_error('Unable to get configuration channels for server {}.'.format(self.server))

    def system_list_groups(self):
        try:
            return self.client.system.listGroups(self.session, self.systemid)
        except xmlrpc.client.Fault as err:
            smt.log_debug('api-call: system.listGroups')
            smt.log_debug('Value passed: ')
            smt.log_debug('  system_id:  {}'.format(self.systemid))
            smt.log_debug("Error: \n{}".format(err))
            smt.fatal_error('Unable to get list of systemgroups for server {}.'.format(self.server))

# ==========================================================

def sync_configchannels(smlm_old, exitonerror):
    """
    Synchronize configchannels

    :param server: Server from which the data needs to be synchronized
    :param smlm_old: Connection information to the previous SMLM
    :param exitonerror: If an item is not present, exit with error when set to True
    :return:
    """
    smt.log_info("start setting configuration channels")
    assigned_configchannels = smlm_old.system_config_listchannels()
    config_channels = []
    for channels in assigned_configchannels:
        config_channels.append(channels.get('name'), exitonerror)
    smt.system_config_set_channels(config_channels)
    smt.log_info("finished setting configuration channels")
    return

def sync_systemgroups(smlm_old, exitonerror):
    """
    Synchronize systemgroups

    :param server: Server from which the data needs to be synchronized
    :param smlm_old: Connection information to the previous SMLM
    :param exitonerror: If an item is not present, exit with error when set to True
    :return:
    """
    smt.log_info("start setting systemgroup membership")
    assigned_groups = smlm_old.system_list_groups()
    available_groups = smt.systemgroup_list_all_groups()
    # smt.log_debug(assigned_groups)
    for group in assigned_groups:
        if group.get('subscribed') == 1:
            smt.log_info(f"Group {group.get('system_group_name')}")
            smt.log_debug(available_groups)
            not_found = True
            for new_group in available_groups:
                smt.log_debug(new_group)
                if group.get('system_group_name') == new_group.get('name'):
                    not_found = False
                    smt.system_set_group_membership(new_group.get('id'), exitonerror)
                    break
            if not_found:
                if exitonerror:
                    smt.fatal_error(f"Group {group.get('system_group_name')} not set. Exiting!!!!!")
                else:
                    smt.log_error(f"Group {group.get('system_group_name')} not set")
    smt.log_info("finished setting systemgroup membership")
    return

def sync_repos(server, smlm_old, exitonerror):
    """
    Synchronize repos

    :param server: Server from which the data needs to be synchronized
    :param smlm_old: Connection information to the previous SMLM
    :param exitonerror: If an item is not present, exit with error when set to True
    :return:
    """
    return

def sync_custominfo(server, smlm_old, exitonerror):
    """
    Synchronize custominfo

    :param server: Server from which the data needs to be synchronized
    :param smlm_old: Connection information to the previous SMLM
    :param exitonerror: If an item is not present, exit with error when set to True
    :return:
    """
    return

def sync_formulars(server, smlm_old, exitonerror):
    """
    Synchronize formulars

    :param server: Server from which the data needs to be synchronized
    :param smlm_old: Connection information to the previous SMLM
    :param exitonerror: If an item is not present, exit with error when set to True
    :return:
    """
    return

def start_sync(args, user, password):
    """
    Start the sync process
    :param args:
    :param user:
    :param password:
    :return:
    """
    smt.suman_login()
    smt.set_hostname(args.server)
    smlm_old = smlm(args.server, args.fromsmlm, user, password, args.skipsslcheck)
    if args.all:
        sync_configchannels(smlm_old, args.exitonerror)
        sync_systemgroups(smlm_old, args.exitonerror)
        sync_repos(args.server, smlm_old, args.exitonerror)
        # sync_custominfo(args.server, smlm_old)
        # sync_formulars(args.server, smlm_old)
        return
    if args.configchannels:
        sync_configchannels(smlm_old, args.exitonerror)
    if args.systemgroups:
        sync_systemgroups(smlm_old, args.exitonerror)
    if args.repos:
        sync_repos(args.server, smlm_old, args.exitonerror)
    # if args.custominfo:
    # sync_custominfo(args.server, smlm_old)
    # if args.formulars:
    # sync_formulars(args.server, smlm_old)
    return

def check_arguments(args):
    """
    Check if the required arguments are passed.

    :param args:
    :return:
    """
    if not args.server:
        smt.log_error("Option --server not given and is required. Aborting operation")
        sys.exit(1)
    if not args.fromsmlm:
        smt.log_error("Option --fromsmlm not given and is required. Aborting operation")
        sys.exit(1)
    if args.user and args.password:
        return args.user, args.password
    if args.user and args.password and args.credential:
        smt.log_error("Option --user and --password or --credential not given and is required. Aborting operation")
        sys.exit(1)
    if args.user and not args.password:
        smt.log_error("Option --user is given but not --password. Aborting operation")
        sys.exit(1)
    if not args.user and args.password:
        smt.log_error("Option --password is given but not --user. Aborting operation")
        sys.exit(1)
    if args.credential:
        try:
            credential = base64.b64decode(args.credential).decode('utf-8')
            user = credential.split(':')[0]
            password = credential.split(':', 1)[1]
            return user, password
        except:
            smt.log_error("Option --credential not correct. Please check. Aborting operation")
            sys.exit(1)
    return None, None

def main():
    """
    Main section
    """
    global smt
    smt = smtools.SMTools("sync_move_server")
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description=('''\
         Usage:
         sync_move_server.py

         This script will only make the given server member of the systemgroups, or assign the correct software channels and repositories.
         It will not create the give objects or check if the data is the same as on the old SMLM server.

               '''))
    parser.add_argument("-s", "--server", help="name of the server moved to the SMLM defined in configsm.yaml")
    parser.add_argument("-f", "--fromsmlm", help="SMLM from which the server has been moved")
    parser.add_argument("-u", "--user", help="user from SMLM server where the server is previously")
    parser.add_argument("-p", "--password", help="password of the user")
    parser.add_argument("-c", "--credential", help="file containing the credentials of the SMLM was previously. "
                                                   "format: user:password base64 encoded")
    parser.add_argument("-a", "--all", action="store_true", default=1,
                        help="Update all information")
    parser.add_argument("-t", "--configchannels", action="store_true", default=0,
                        help="Add configuration channels from previous to current.")
    parser.add_argument("-g", "--systemgroups", action="store_true", default=0,
                        help="Add systemgroups from previous to current.")
    parser.add_argument("-r", "--repos", action="store_true", default=0,
                        help="Add repositories from previous to current.")
    #parser.add_argument("-i", "--custominfo", action="store_true", default=0,
    #                    help="Add custominfo from previous to current.")
    #parser.add_argument("-o", "--formulars", action="store_true", default=0,
    #                    help="Add formulars from previous to current.")
    parser.add_argument("-e", "--exitonerror", action="store_true", default=0,
                        help="When set, exit when a item is missing on the new server. Otherwise only report.")
    parser.add_argument("-k", "--skipsslcheck", action="store_true", default=0,
                        help="When set, exit when a item is missing on the new server. Otherwise only report.")
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0, June 7, 2025')
    args = parser.parse_args()
    smt.log_info("Start")
    smt.log_debug("Given options: {}".format(args))
    user, password = check_arguments(args)

    start_sync(args, user, password)

    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
