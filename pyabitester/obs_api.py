import requests
import xml.etree.ElementTree as ET

class ObsApi():

    def __init__(self, url, auth):
        self.url = url
        self.auth = auth
        self.session = requests.Session()

    def get_binary(self, project_name, repository_name, architecture_name, package_name, file_name):
        get_binary_url = f"/build/{project_name}/{repository_name}/{architecture_name}/{package_name}/{file_name}"
        response = self.session.get(self.url + get_binary_url, verify=False, auth=self.auth)
        if response.headers['content-type'] == "application/x-rpm":
            return response.content
        return None

    def binary_list(self, project_name, repository_name, architecture_name, package_name):
        '''
        <binarylist>
            <binary filename="hello-2.10-3.1.x86_64.rpm" size="58352" mtime="1617270174">
            </binary>
        </binarylist>
        '''
        binary_list_url = f"/build/{project_name}/{repository_name}/{architecture_name}/{package_name}"
        response = self.session.get(self.url + binary_list_url, verify=False, auth=self.auth)
        binary_filename_list = []
        binarylist = ET.fromstring(response.text)
        for binary in binarylist:
            binary_filename_list.append(binary.attrib["filename"])
        return binary_filename_list

    def repo_list(self, project_name):
        '''
        <directory>
            <entry name="openSUSE_Tumbleweed">
            </entry>
            <entry name="openSUSE_Leap_15.3">
            </entry>
        </directory>
        '''
        repo_list_url = f"/build/{project_name}"
        response = self.session.get(self.url + repo_list_url, verify=False, auth=self.auth)
        repo_list = []
        directory = ET.fromstring(response.text)
        for entry in directory:
            repo_list.append(entry.attrib["name"])
        return repo_list

    def meta_pkg(self, project_name, package_name):
        '''
        <package name="package_1">
            <title></title>
            <description>Test package</description>
            <devel project="home:Admin" package="package_2">
            </devel>
        </package>
        '''
        # Actually only returns "name" and "project" (if existent) fields
        meta_pkg_url = f"/source/{project_name}/{package_name}/_meta"
        response = self.session.get(self.url + meta_pkg_url, verify=False, auth=self.auth)
        meta_xml = ET.fromstring(response.text)
        return meta_xml.attrib

    def showlinked(self, project_name, package_name):
        '''
        <collection>
            <package name="hello_world" project="home:Admin:branches:home:Admin">
            </package>
            <package name="hello_world2" project="home:Admin:branches:home:Admin">
            </package>
        </collection>
        '''
        showlinked_url = f"/source/{project_name}/{package_name}?cmd=showlinked"
        response = self.session.post(self.url + showlinked_url, verify=False, auth=self.auth)
        linked_package_list = []
        collection = ET.fromstring(response.text)
        for package in collection:
            linked_package_list.append(package.attrib)

        return linked_package_list