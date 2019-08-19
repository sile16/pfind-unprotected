# pfind-unprotected
Finds volumes not in a protection group on a Pure FlashArray.


```
usage: pfind-unprotected.py [-h] [--user USER] [--pass PASSWORD]
                            [--api-token API_TOKEN]
                            [--enable-check [{local,remote,either,nocheck}]]
                            array

Find unprotected volumes on a Pure FlashArray

positional arguments:
  array                 Array FQDN or IP

optional arguments:
  -h, --help            show this help message and exit
  --user USER           username, required if no api-token
  --pass PASSWORD       password - will prompt if missing
  --api-token API_TOKEN
                        api-token (not required if user/pass is provided)
  --enable-check [{local,remote,either,nocheck}]
                        Check if local, or remote schedule is enabled on PG.
                        Remote checks also ensure that there is at least 1
                        allowed target. (default: either)
```

# Example
```
python3 pfind-unprotected.py --api-token eabx168-eb95-2930-da9f-bc1a3af270 --enable-check either  10.10.4.1

Volume mr-matt-disabled is not in a local or remote PG with a schedule enabled or allowed target.
Volume mr-matt-not-in-pg is not in a local or remote PG with a schedule enabled or allowed target.
Volume mr-matt-remote-pg is not in a local or remote PG with a schedule enabled or allowed target.
```
