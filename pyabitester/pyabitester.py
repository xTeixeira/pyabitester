import requests
import sys
import urllib
import re
from pyabitester.signature_auth import SignatureAuth
from pyabitester.obs_api import ObsApi
import argparse
import click
from urllib.parse import urlparse
import keyring

latest_sle = "SUSE:SLE-15-SP7:GA"
obs_url = "https://api.opensuse.org"
ibs_url = "https://api.suse.de"

def get_canon_project(api, project_name, package_name):
    # Get linked SUSE:Maintenance projects from SLE codestream
    pkglist = [pkg for pkg in api.showlinked(project_name, package_name) if "SUSE:Maintenance" in pkg["project"]]
    # Get latest SUSE:Maintenance project
    if len(pkglist) > 0:
        pkglist.sort(reverse=True, key=lambda pkg : pkg["project"])
        return pkglist[0]["project"], pkglist[0]["name"]

    # In the case of SLE projects, If there is no SUSE:Maintenance project linked, it means the latest version is from a GA release.
    # So we look for the canon project in the package's meta, which will also work for Factory or other OBS projects.
    package_meta = api.meta_pkg(project_name, package_name)
    if package_meta:
        return package_meta["project"], package_meta["name"]

    raise RuntimeError('could not find suitable project to download rpm packages from')

@click.command()
@click.option('--obs-user', prompt=f'User name for {obs_url}', help='OBS user name')
@click.option('--ssh-key', prompt='Path to ssh key file', help='SSH key file path')
@click.option('--arch', default="x86_64")
@click.password_option("--obs-pass", prompt='Password for OBS user',  confirmation_prompt=True, prompt_required=False, help='OBS password')
@click.argument('package-name')
def cli(obs_user, obs_pass, ssh_key, package_name, arch):
    ibs_api = ObsApi(ibs_url, SignatureAuth(obs_user, ssh_key))

    if not obs_pass:
        obs_pass = keyring.get_password(urlparse(obs_url).netloc, obs_user)
        if not obs_pass:
            obs_pass = click.prompt('Password for OBS user', hide_input=True, confirmation_prompt=True)
            try:
                keyring.set_password(urlparse(obs_url).netloc, obs_user, obs_pass)
            except keyring.errors.PasswordSetError:
                print("Failed to store password in keyring")
                exit(1)

    obs_api = ObsApi(obs_url, auth=requests.auth.HTTPBasicAuth(obs_user, obs_pass))
    print(get_repo(obs_api, "openSUSE:Factory", package_name))
    print(get_repo(ibs_api, latest_sle, package_name))

if __name__ == '__main__':
    cli()


