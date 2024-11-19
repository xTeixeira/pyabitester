import requests
import xml.etree.ElementTree as ET

class ObsApi():

    def __init__(self, url, auth):
        self.url = url
        self.auth = auth
        self.session = requests.Session()

    def meta_pkg(self, project, package_name):
        # Actually only returns "name" and "project" fields
        meta_pkg_url = "/source/{}/{}/_meta".format(project, package_name)
        response = self.session.get(self.url + meta_pkg_url, verify=False, auth=self.auth)
        meta_xml = ET.fromstring(response.text)
        return meta_xml.attrib

    def showlinked(self, project, package_name):
        showlinked_url = "/source/{}/{}?cmd=showlinked".format(project, package_name)
        response = self.session.post(self.url + showlinked_url, verify=False, auth=self.auth)
        linked_package_list = []
        packages_xml = ET.fromstring(response.text)
        for package in packages_xml:
            linked_package_list.append(package.attrib)

        return linked_package_list