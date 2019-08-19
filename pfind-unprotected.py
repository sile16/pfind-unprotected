# Matt Robertson - Pure Storage 2019
# List all volumes that do are not parts of an enabled protectiong group

import argparse
import purestorage
import getpass
import datetime
import dateutil.parser
import urllib3
import re
from datetime import timedelta
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#checks for at least 1 allowed target on the protection group
def target_check(item):
    if 'targets' not in item or not item['targets']:
        return False
    for t in item['targets']:
        if t['allowed']:
            return  True
    return False

def main():
    parser = argparse.ArgumentParser(description='Find unprotected volumes on a Pure FlashArray',
                                     allow_abbrev=False)
    parser.add_argument(dest='array', help='Array FQDN or IP')
    parser.add_argument('--user',  action='store', dest='user', help='username, required if no api-token')
    parser.add_argument('--pass',  action='store', dest='password', help='password - will prompt if missing')
    parser.add_argument('--api-token', dest='api_token', action='store', help='api-token')
    parser.add_argument('--enable-check',
                    dest='enable_check',
                    default='either',
                    const='all',
                    nargs='?',
                    choices=['local', 'remote', 'either', 'nocheck'],
                    help='Check if local, or remote schedule is enabled on PG.  \
                          Remote checks also ensure that there is at least 1 allowed target. (default: %(default)s)')
    args = parser.parse_args()


    #parse Auth info and connect to array
    if args.api_token:
        array = purestorage.FlashArray(args.array, api_token=args.api_token)
    else:
        if args.user:
            if not args.password:
                args.password = getpass.getpass("Password for {} :".format(args.user))
            
            array =  purestorage.FlashArray(args.array, username=args.user, password=args.password)
        else:
            #error neither api token or user must be specified.
            parser.error('Must provide either an api-token or username.')
    
    #check to see if the pg has an enabled target
    target_allowed_pgs = {}
    for pg in array.list_pgroups():
        if target_check(pg):
            target_allowed_pgs[pg['name']] = True

    # get list of protection groups
    # check the enabled status per the enabled check
    checked_pgs = {}
    for pg in array.list_pgroups(schedule=True):
        if args.enable_check == 'nocheck':
            checked_pgs[pg['name']] = pg
        elif args.enable_check == 'local':
            if pg['snap_enabled']:
                checked_pgs[pg['name']] = pg
        elif args.enable_check == 'remote':
            if pg['replicate_enabled'] and  \
               pg['name'] in target_allowed_pgs:
                checked_pgs[pg['name']] = pg
        elif args.enable_check == 'either':
            if pg['snap_enabled'] or ( pg['replicate_enabled'] and  \
                                       pg['name'] in target_allowed_pgs):
                checked_pgs[pg['name']] = pg

    
    # get list of all protected volumes and ensure they are in a PG
    # That is enabled per the enabled check
    checked_vols = {}
    for vol in array.list_volumes(protect=True):
        if vol['protection_group'] in checked_pgs:
            checked_vols[vol['name']] = True
    
    #make the output message correct
    if args.enable_check == 'either':
        msg = 'is not in a local or remote PG with a schedule enabled and allowed target.'
    elif args.enable_check == 'nocheck':
        msg  = 'is not in a PG.'
    elif args.enable_check == 'local':
        msg = "is not in a PG with a snap schedule enabled."
    elif args.enable_check == 'remote':
        msg = "is not in a PG with a remote schedule enabled and allowed target."

    # Get all volumes and list the ones not potected.
    all_vols = array.list_volumes()
    all_vols = sorted(all_vols, key=lambda k: k['name'])
    for vol in all_vols:
        if vol['name'] not in checked_vols:
            print("Volume {} {}".format(vol['name'], msg))


if __name__ == '__main__':
    main()