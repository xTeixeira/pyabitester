import requests
import sys
import urllib
import re
from signature_auth import SignatureAuth
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("package_name")
parser.add_argument("user")
parser.add_argument("ssh_key_path")
args = parser.parse_args()

package_name = sys.argv[1]
latest_sle = "SUSE:SLE-15-SP7:GA"
obs_url = "https://api.opensuse.org"
ibs_url = "https://api.suse.de"
showlinked_url = "/source/{}/{}?cmd=showlinked".format(latest_sle, package_name)

response = requests.post(ibs_url + showlinked_url, verify=False, auth=SignatureAuth(args.user, args.ssh_key_path))

print(response.text)

