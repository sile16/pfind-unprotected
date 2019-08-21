# Matt Robertson - Pure Storage 2019
# List all volumes that do are not parts of an enabled protectiong group

import argparse
import purestorage
import getpass
import urllib3
from concurrent.futures import ThreadPoolExecutor

#Disable the SSL certificate warning
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
    parser.add_argument('--api-token', dest='api_token', action='store', 
                        help='api-token (not required if user/pass is provided')
    parser.add_argument('--enable-check',
                    dest='enable_check',
                    default='either',
                    const='all',
                    nargs='?',
                    choices=['local', 'remote', 'either', 'nocheck'],
                    help='Check if local, or remote schedule is enabled on PG.  \
                          Remote checks also ensure that there is at least 1 allowed target. (default: %(default)s)')
    parser.add_argument('--quiet', default=False, action='store_true', help='Only print vol name')
    parser.add_argument('--ignore', default='',help='ignores volumes that contain the ignore string' )
    args = parser.parse_args()


    try: 
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

        
        
        # run all the API calls in threads up front simultaniously
        # This is a pretty slick way to use threads!  I like it!
        pool = ThreadPoolExecutor(5)
        list_pgroups_f = pool.submit(array.list_pgroups)
        list_pgroups_schedule_f = pool.submit(array.list_pgroups, schedule=True)
        list_hgroups_f = pool.submit(array.list_hgroups)
        list_volumes_connect_f  = pool.submit(array.list_volumes,connect=True)
        list_volumes_f = pool.submit(array.list_volumes)


        # get list of protection groups
        # check the enabled status per the enabled check
        # make sure the protection group is actually enabled
        pg_schedules = {}
        for pg in list_pgroups_schedule_f.result():
            pg_schedules[pg['name']] = pg
            

        #find all the volumes, hosts, & hostgroups that are in the protection groups
        protected_vols = {}
        protected_hosts = {}
        protected_hgroups = {}
        for pg in list_pgroups_f.result():
            # Check the PG to make sure it meets the rules:
            schedule = pg_schedules[pg['name']] 
            if args.enable_check == 'nocheck':
                pass
            elif args.enable_check == 'local' and \
                schedule['snap_enabled']:
                pass
            elif args.enable_check == 'remote' and  \
                schedule['replicate_enabled'] and target_check(pg):
                pass
            elif args.enable_check == 'either' and \
                    ( schedule['snap_enabled'] or  \
                    ( schedule['replicate_enabled'] and target_check(pg) )):
                pass
            else:
                continue


            #Passed our checks now lets keep track of protected objects
            if pg['volumes']:
                for v in pg['volumes']:
                    protected_vols[v] = True
            if pg['hosts']:
                for h in pg['hosts']:
                    protected_hosts[h] = True
            if pg['hgroups']: 
                for hg in pg['hgroups']:
                    protected_hgroups[hg] = True
        
        #find all the hosts that are in protected host groups
        for hg in list_hgroups_f.result():
            if hg['name'] in protected_hgroups:
                for h in hg['hosts']:
                    protected_hosts[h] = True
        
        #find all volumes that are mapped to either a protected host or hgroup
        for v in list_volumes_connect_f.result(): 
            if v['host'] in protected_hosts or v['hgroup'] in protected_hgroups:
                protected_vols[v['name']] = True
        
        
        #make the output message correct
        if args.enable_check == 'either':
            msg = ' is not in a local or remote PG with a schedule enabled and allowed target.'
        elif args.enable_check == 'nocheck':
            msg = ' is not in a PG.'
        elif args.enable_check == 'local':
            msg = " is not in a PG with a snap schedule enabled."
        elif args.enable_check == 'remote':
            msg = " is not in a PG with a remote schedule enabled and allowed target."
        
        if args.quiet:
            msg = ""

        # Get all volumes and list the ones not protected.
        all_vols = list_volumes_f.result()
        all_vols = sorted(all_vols, key=lambda k: k['name'])
        for vol in all_vols:
            #ignore volumes if they have this string.
            if args.ignore:
                if args.ignore in vol['name']:
                    continue
            if vol['name'] not in protected_vols:
                print("{} {}".format(vol['name'], msg))
    except AttributeError as e:
        print("Error connecting to array, check IP, network: {}".format(e))
        quit()


if __name__ == '__main__':
    main()