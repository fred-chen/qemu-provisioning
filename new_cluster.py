#!/usr/bin/env python3

import yaml
import os
import getopt, sys
import urllib.parse as parse

g_settings = {}

def load_settings():
    g_settings.update (yaml.safe_load(open("settings.yaml").read()))

def basenameurl(url: str):
    basename = os.path.basename(url)
    return basename
    
def download_to(url, target_dir=None):
    import requests
    if not target_dir:
        target_dir = g_settings["cloud-image-dir"]
    filepath = target_dir + "/" + basenameurl(url)
    if not os.path.exists(filepath):
        print("downloading to " + filepath)
        response = requests.get(url)
        open(filepath, "wb").write(response.content)
    return filepath

def check_path(path: str):
    if not os.path.exists(path):
        raise ( Exception("{} does not exist!".format(path)) )

def usage(err: str):
    print(err)
    exit(1)

def apply_handleopts(settings: dict):
    try:
        options, args = getopt.gnu_getopt(sys.argv[2:], "f:", ["configfile="])
    except getopt.GetoptError as err:
        usage(err)
    for o, a in options:
        if(o in ('-f', '--configfile')):
            settings["configfile"] = a
    for operation in args:
        print(operation)

def create_cluster(settings: dict) -> bool:
    clusterName    = settings["clusterName"]
    systemDiskSize = settings["systemDiskSize"]
    imagePath      = settings["imagePath"]
    
    if os.path.exists(clusterName):
        return False
    else:
        if parse.urlparse(imagePath).scheme in ('http', 'https'):
            localImage = download_to(imagePath)
        else:
            localImage = imagePath    
        check_path(localImage)
        print("using {}".format(localImage))
        
        os.mkdir(clusterName)
        os.mkdir(clusterName + "/" + "cloud-init")

def create_node(settings: dict):
    pass

def cmd_apply():
    settings_for_apply = {}
    apply_handleopts (settings_for_apply)
    configfile = settings_for_apply["configfile"]
    
    if os.path.exists(configfile):
        cluster_settings = yaml.safe_load(open(configfile).read())
        str = yaml.safe_dump(cluster_settings)
        print(str)
        
        create_cluster(cluster_settings)
            
if __name__ == "__main__":
    load_settings()
    
    command = sys.argv[1]
    # argv[1] must be one of:
    match command:
        case 'apply':
            cmd_apply()
        case other:
            usage ('command "{}" not recognized.'.format(command))
    
