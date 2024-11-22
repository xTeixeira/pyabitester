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
import os
import rpm
import stat

latest_sle = "SUSE:SLE-15-SP7:GA"
obs_url = "https://api.opensuse.org"
ibs_url = "https://api.suse.de"

def unpack_rpm(h, fd, prefix):
    files = rpm.files(h)
    payload = rpm.fd(fd, 'r', h['payloadcompressor'])
    archive = files.archive(payload)
    for f in archive:
        os.makedirs(f'{prefix}/{f.dirname}', exist_ok=True)
        fn = f'{prefix}/{f.name}'
        if stat.S_ISREG(f.mode):
            if archive.hascontent():
                wfd = rpm.fd(fn, 'w')
                archive.readto(wfd)
                wfd.close()
                # handle hardlinks
                if f.nlink > 1:
                    for l in f.links:
                        if l.name != f.name:
                            ln = f'{prefix}/{l.name}'
                            os.link(fn, ln)
        elif stat.S_ISDIR(f.mode):
            os.makedirs(fn, exist_ok=True)
        elif stat.S_ISLNK(f.mode):
            os.symlink(f.linkto, fn)

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

def get_repository(api, canon_project_name):
    repo_list = api.repo_list(canon_project_name)
    # Try to guess the correct repo. For maintenance projects for now we simply pick one with "SUSE_SLE" in the name.
    # For everything else it's usually "standard"
    # No option is provided for the user to choose the repo manually, although maybe they should be prompted if no suitable repo is found.
    for repo in repo_list:
        if "SUSE_SLE" in repo:
            return repo
    return "standard"

def get_binaries(api, project_name, package_name, architecture_name):
    binaries = []
    canon_project_name, canon_package_name = get_canon_project(api, project_name, package_name)
    repository_name = get_repository(api, canon_project_name)
    for binary_filename in api.binary_list(canon_project_name, repository_name, architecture_name, canon_package_name):
        # Only download packages for the desired arch
        if f"{architecture_name}.rpm" not in binary_filename:
            continue

        binary_content = api.get_binary(canon_project_name, repository_name, architecture_name, canon_package_name, binary_filename)

        if binary_content:
            binaries.append({"file_name" : binary_filename, "file_content" : binary_content})

    return binaries

@click.command()
@click.option('--obs-user', prompt=f'User name for {obs_url}', help='OBS user name')
@click.option('--ssh-key', prompt='Path to ssh key file', help='SSH key file path')
@click.option('--arch', default="x86_64")
@click.password_option("--obs-pass", prompt='Password for OBS user',  confirmation_prompt=True, prompt_required=False, help='OBS password')
@click.argument('package-name')
def cli(obs_user, obs_pass, ssh_key, package_name, arch):

    if not obs_pass:
        obs_pass = keyring.get_password(urlparse(obs_url).netloc, obs_user)
        if not obs_pass:
            obs_pass = click.prompt('Password for OBS user', hide_input=True, confirmation_prompt=True)
            try:
                keyring.set_password(urlparse(obs_url).netloc, obs_user, obs_pass)
            except keyring.errors.PasswordSetError:
                print("Failed to store password in keyring")
                exit(1)

    sle_download_path = f"sle/{package_name}"
    factory_download_path = f"factory/{package_name}"

    if not os.path.exists(sle_download_path):
        ibs_api = ObsApi(ibs_url, SignatureAuth(obs_user, ssh_key))
        ibs_binaries = get_binaries(ibs_api, latest_sle, package_name, arch)
        os.makedirs(sle_download_path)

        for rpm_file in ibs_binaries:
            with open(f'{sle_download_path}/{rpm_file["file_name"]}', 'wb') as file:
                file.write(rpm_file["file_content"])

    if not os.path.exists(factory_download_path):
        obs_api = ObsApi(obs_url, auth=requests.auth.HTTPBasicAuth(obs_user, obs_pass))
        obs_binaries = get_binaries(obs_api, "openSUSE:Factory", package_name, arch)
        os.makedirs(factory_download_path, exist_ok=True)

        for rpm_file in obs_binaries:
            with open(f'{factory_download_path}/{rpm_file["file_name"]}', 'wb') as file:
                file.write(rpm_file["file_content"])

    for file in [file for file in os.listdir(sle_download_path) if os.path.isfile(os.path.join(f"{sle_download_path}/", file))]:
        ts = rpm.TransactionSet()
        os.makedirs(f"./sle/{package_name}/contents", exist_ok=True)
        ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)

        fd = os.open(f"sle/{package_name}/{file}", os.O_RDONLY)
        hdr = ts.hdrFromFdno(fd)

        unpack_rpm(hdr, fd, f"./sle/{package_name}/contents")
        os.close(fd)


if __name__ == '__main__':
    cli()


