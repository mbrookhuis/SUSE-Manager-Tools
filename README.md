# Uyuni-Tools version 2

This is the new version of the Uyuni Tools. The major changes are:
- log_level can be set separately for screen and files
- for some of the major components in system_update.py it can be configured how the script should react. For example exit the script or only report an error and continue.
- optimized code
- only use https as the connection between the scripts and Uyuni Server
- the default location for the scripts is /opt/uyuni-tools
- each script will have a --help to see all available parameters
- added monitoring for system_update.py. See [monitoring](documentation/monitoring.md) for more information

The following scripts will not be longer part of the set. Please let me know if you want them back:
- cve_report.py
- channel_cloner.py

What is still not included:
- The script system_update.py will perform an update of the maintenance stack before applying the other updates. This is only available for "zypper" (SLES). Plan to add other distributions in the future.

General configuration is done in configsm.yaml:
- The file configsm.yaml should be in the same directory as the scripts. And before using check the file and correct the information.
- Contains the login credentials and the Uyuni Server (which should be given in FQDN) 
- Contains the location of the log and script directories
- Should mail be sent in case of an error and to whom?
- Information needed for SP migration for system update
- Containg the settings for logging and how the system_update.py script should react.
- Run update_configsm.sh first after every update of the tools!!!


The following scripts are included (click on the link for more information):
- [add_cve_to_project.py](documentation/add_cve_to_project.md)
- [create_software_project.py](documentation/create_software_project.md)
- [group_system_update.py](documentation/group_system_update.md)
- [sync_stage.py](documentation/sync_stage.md)
- [system_update.py](documentation/system_update.md)

 
- create_repos.py
From a pre-defined yaml channels will be created in the give parent channels. This also includes the creation of the repositories and sync schedule. Also the initial synchronization can be started.

- smtools.py
This is the library containing all functions and cannot be executed.

- sync_channel.py
This will clone the give channel with the channel it is cloned from.

- sync_environment.py
This script can be used to updated (merge the patches and packages that are available in the channels they are cloned from) an environment across all lifecycle projects. 

- system_rereg.py
When a system needs to be moved from Uyuni Server to a Uyuni Proxy or from a Uyuni Proxy to another Uyuni Proxy this script can be used.


Known Issues:
=============
- During the execution a python dump is written telling something related to CONFIGSM, this will in general mean that your configsm.yaml is not correct. Please run update_configsm.sh. If you still have problems, compare the configsm.yaml part of this git with yours.
- When you receive an error regarding the SSL certificate (for example: "ssl.CertificateError: hostname 'mbsuma4' doesn't match 'mbsuma4.mb.int'") there are 2 possible causes:
* In configsm.yaml the option [suman][server] should contain the FQDN of the Uyuni Server.
* The Uyuni Server certificate is not imported. Perform the following steps:
  - copy from the Uyuni Server /srv/www/htdocs/pub/RHN-ORG-TRUSTED-SSL-CERT to /etc/pki/trust/anchors/ on the server you are running the scripts.
  - run the command (as root): update_ca_certificates

How to use:
- Each script will have a help option: --help 

GNU Public License. No warranty. No Support 
For question/suggestions/bugs mail: michael.brookhuis@suse.com
Created by: SUSE Michael Brookhuis July 2020



