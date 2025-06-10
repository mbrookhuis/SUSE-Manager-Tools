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

    def __init__(self, smt, server, fromsmlm, user, password):
        self.smt = smt
        self.server = server
        self.fromsmlm = fromsmlm
        self.user = user
        self.password = password

        self.set_hostname()
        self.login_smlm()

    def login_smlm(self):
        """
        Login to previous SMLM
        :return: error, client connections, and session key
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect_ex(self.fromsmlm, 443)
        except socket.error as msg:
            self.smt.fatal_error(f"Unable to login to SUSE Manager server {self.fromsmlm}\nError: {msg}")
        self.client = xmlrpc.client.Server("https://" + self.fromsmlm + "/rpc/api")
        try:
            self.session = self.client.auth.login(self.user, self.password)
        except xmlrpc.client.Fault as msg:
            self.smt.fatal_error(f"Unable to login to SUSE Manager server {self.fromsmlm}.\nError: {msg}")
        return

    def set_hostname(self, fatal=True):
        """
        Set hostnam for global use.
        """
        self.get_server_id(fatal)
        self.smt.log_info("Hostname : {}".format(self.server))
        self.smt.log_info("Systemid : {}".format(self.systemid))

    def get_server_id(self, fatal=True):
        """
        Get system Id from host
        """
        hostname = self.server

        all_sid = ""
        try:
            all_sid = self.client.system.getId(self.session, hostname)
        except xmlrpc.client.Fault:
            self.smt.fatal_error("Unable to get systemid from system {}. Is this system registered?".format(hostname))
        system_id = 0
        for x in all_sid:
            if system_id == 0:
                system_id = x.get('id')
            else:
                if fatal:
                    self.smt.fatal_error("Duplicate system {}. Please fix and run again.".format(hostname))
                else:
                    self.smt.log_error("Duplicate system {}. Please fix and run again.".format(hostname))
                    self.smt.log_debug(
                        "The following system id have been found for system {}:\n{}".format(hostname, all_sid))
        if system_id == 0:
            if fatal:
                self.smt.fatal_error(
                    "Unable to get systemid from system {}. Is this system registered?".format(hostname))
            else:
                self.smt.log_error(
                    "Unable to get systemid from system {}. Is this system registered?".format(hostname))
        self.systemid = system_id
        return system_id

    def system_config_listchannels(self):
        try:
            return self.client.system.config.listChannels(self.session, self.systemid)
        except xmlrpc.client.Fault as err:
            self.smt.log_debug('api-call: system.listChannels')
            self.smt.log_debug('Value passed: ')
            self.smt.log_debug('  system_id:  {}'.format(self.systemid))
            self.smt.log_debug("Error: \n{}".format(err))
            self.smt.fatal_error('Unable to get configuration channels for server {}.'.format(self.server))

# ==========================================================

def sync_configchannels(server, smlm_old, exitonerror):
    """
    Synchronize configchannels

    :param server: Server from which the data needs to be synchronized
    :param smlm_old: Connection information to the previous SMLM
    :param exitonerror: If an item is not present, exit with error when set to True
    :return:
    """
    assigned_configchannels = smlm_old.system_config_listchannels()
    config_channels = []
    for channels in assigned_configchannels:
        config_channels.append(channels)

    smt.log_debug("config_channels: {}".format(config_channels))
    smt.log_debug(server)
    smt.log_debug(exitonerror)

    return

def sync_systemgroups(server, smlm_old, exitonerror):
    """
    Synchronize systemgroups

    :param server: Server from which the data needs to be synchronized
    :param smlm_old: Connection information to the previous SMLM
    :param exitonerror: If an item is not present, exit with error when set to True
    :return:
    """
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
    smlm_old = smlm(__smt, args.server, args.fromsmlm, user, password)
    if args.all:
        sync_configchannels(args.server, smlm_old)
        sync_systemgroups(args.server, smlm_old)
        sync_repos(args.server, smlm_old)
        # sync_custominfo(args.server, smlm_old)
        # sync_formulars(args.server, smlm_old)
        return
    if args.configchannels:
        sync_configchannels(args.server, smlm_old)
    if args.systemgroups:
        sync_systemgroups(args.server, smlm_old)
    if args.repos:
        sync_repos(args.server, smlm_old)
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

    if not args.user or not args.password or not args.credential:
        smt.log_error("Option --user and --password or --credentials not given and is required. Aborting operation")
        sys.exit(1)
    elif args.credentials:
        try:
            credentials = base64.b64decode(args.credentials).decode('utf-8')
            user = credentials.split(':')[0]
            password = credentials.split(':', 1)[1]
            return user, password
        except:
            smt.log_error("Option --credentials not correct. Please check. Aborting operation")
            sys.exit(1)
    elif args.user and not args.password:
        smt.log_error("Option --user is given but not --password. Aborting operation")
        sys.exit(1)
    elif not args.user and args.password:
        smt.log_error("Option --password is given but not --user. Aborting operation")
        sys.exit(1)
    elif not args.user and args.password:
        user = args.user
        password = args.password
        return user, password
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
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0, June 7, 2025')
    args = parser.parse_args()
    smt.log_info("Start")
    smt.log_debug("Given options: {}".format(args))
    user, password = check_arguments(args)

    start_sync(args, user, password)

    smt.close_program()


if __name__ == "__main__":
    SystemExit(main())
