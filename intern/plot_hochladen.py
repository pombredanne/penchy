#!/usr/bin/env python

from xml.etree import ElementTree  # fuer xml
# import pythonfs ?

dest_server_id = "server001"  # <id> in settings.xml
picture = "grafik.png"
xmlns = '{http://maven.apache.org/SETTINGS/1.0.0}'  # xml namespace


def read_login_data(dest_id):
    tree = ElementTree.parse("settings.xml")
    xpath = './/%sserver[%sid="%s"]' % (xmlns, xmlns, dest_id)
    servers = tree.findall(xpath)

    username = servers[0].findtext(".//%susername" % xmlns)
    password = servers[0].findtext(".//%spassword" % xmlns)
    return username, password


def main():
    username, password = read_login_data(dest_server_id)
    print username, password

if __name__ == '__main__':
    main()