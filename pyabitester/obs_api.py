import requests
import xml.etree.ElementTree as ET

class ObsApi():

    def __init__(self, url, auth):
        self.url = url
        self.auth = auth
        self.session = requests.Session()

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