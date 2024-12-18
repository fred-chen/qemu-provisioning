#!/usr/bin/env python3

import os
import stat
import getopt
import sys
import urllib.parse as parse
import platform
import distro
import subprocess
import random
import requests
import socket
import yaml

g_settings = {}


def load_settings():
    """load settings from settings.yaml in script directory
    """
    g_settings.update(yaml.safe_load(
        open(script_path() + "/" + "settings.yaml", encoding='utf-8').read()))


def basenameurl(url: str) -> str:
    """get the last part of a url

    Args:
        url (str): a url string

    Returns:
        str: the basename of the url
    """
    basename = os.path.basename(url)
    return basename


def download_to(url: str, target_dir: str = None) -> str:
    """download a file indicated by the url to target_dir

    Args:
        url (str): the file to download in url form
        target_dir (str, optional): the target folder to store the downloaded 
                                    file. Defaults to None.

    Returns:
        str: the filepath if successfully downloaded, otherwise None
    """
    if not target_dir:
        target_dir = g_settings["cloud-image-dir"]
    filepath = target_dir + "/" + basenameurl(url)
    if not os.path.exists(filepath):
        print("downloading to " + filepath)
        response = requests.get(url, timeout=None)
        open(filepath, "wb").write(response.content)
    return filepath


def check_path(path: str):
    """check the existence of a path

    Args:
        path (str): the path to check

    Returns:
        str: return the path if exists, otherwize return 
                the cloud-image-dir if exits, else None
    """
    localpath = path
    if not os.path.exists(localpath):
        localpath = g_settings["cloud-image-dir"] + "/" + localpath
        if not localpath:
            raise ValueError(f"{path} does not exist!")
    return localpath


def script_path() -> str:
    """return the local path where the script is under

    Returns:
        str: the path
    """
    return os.path.dirname(__file__)


def usage(err: str):
    """print the usage and exit

    Args:
        err (str): the error message that printed along with usage text
    """
    print(f"Usage: {os.path.basename(sys.argv[0])} deploy -f xxx.yaml")
    print(err)
    sys.exit(1)

# this function is directly from xend/server/netif.py and is thus
# available under the LGPL,
# Copyright 2004, 2005 Mike Wray <mike.wray@hp.com>
# Copyright 2005 XenSource Ltd


def random_mac(mac_type="xen"):
    """Generate a random MAC address.

    00-16-3E allocated to xensource
    52-54-00 used by qemu/kvm

    The OUI list is available at http://standards.ieee.org/regauth/oui/oui.txt.

    The remaining 3 fields are random, with the first bit of the first
    random field set 0.

    >>> random_mac().startswith("00:16:3E")
    True
    >>> random_mac("foobar").startswith("00:16:3E")
    True
    >>> random_mac("xen").startswith("00:16:3E")
    True
    >>> random_mac("qemu").startswith("52:54:00")
    True

    @return: MAC address string
    """
    ouis = {'xen': [0x00, 0x16, 0x3E], 'qemu': [0x52, 0x54, 0x00]}

    try:
        oui = ouis[mac_type]
    except KeyError:
        oui = ouis['xen']

    mac = oui + [
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))


def get_free_port():
    """get a free port number

    Returns:
        int: a port number
    """
    sock = socket.socket()
    sock.bind(('', 0))
    return sock.getsockname()[1]


def exe(cmd: str) -> int:
    """run a command

    Args:
        cmd (str): the command string

    Raises:
        ValueError: error raised if failed to execute the command

    Returns:
        int: the exit code of the command
    """
    return_code = subprocess.call(cmd, shell=True)
    if return_code != 0:
        raise ValueError(f"error when executing:\n {cmd}\n")
    return return_code


def apply_handleopts(settings: dict):
    """handle command line arguments

    Args:
        settings (dict): the setting dict to store the settings
    """
    try:
        options, args = getopt.gnu_getopt(sys.argv[2:], "f:", ["configfile="])
    except getopt.GetoptError as err:
        usage(err)
    for option, arg in options:
        if option in ('-f', '--configfile'):
            settings["configfile"] = arg
    for operation in args:
        print(operation)


class IDeployer:
    """A common interface for all Deployers
    """

    def __init__(self, settings: dict):
        self.settings = settings
        self.flatten_settings()

    def create_cluster(self) -> bool:
        raise ValueError("Error: not implemented")

    def flatten_settings(self):
        # use cluster settings as defaults and populate to all nodes
        nodes = self.settings["nodes"]
        for node in nodes:
            for key in ("clusterName", "domainName", "imagePath",
                        "systemDiskSize", "dataDiskSizes", "cpu", "mem", "mtu", "gateway",
                        "nameserver", "guestOs", "authorized-keys", "qemubin"):
                node[key] = self.settings[key] if key not in node else node[key]


class Deployer_Ubuntu(IDeployer):
    def __init__(self, settings: dict):
        settings["qemubin"] = "qemu-system-x86_64"
        IDeployer.__init__(self, settings)

    def deploy(self) -> bool:
        clusterName = self.settings["clusterName"]

        if os.path.exists(clusterName):
            # cluster folder already exists
            print(f"folder {clusterName} already exists.", file=sys.stderr)
            return False
        else:
            # create cluster folder
            # cluster
            #   |- start_cluster.sh
            #   |- stop_cluster.sh
            #   |- node1
            #   |    |- system.qcow2
            #   |    |- data.qcow2
            #   |    |- start.sh
            #   |    |- cloud-init
            #   |         |- meta-data
            #   |         |- user-data
            #   |         |- network-config
            #   |         |- cloud-init-provisioning.iso
            #   |- node2
            #   |- node3
            os.mkdir(clusterName)
            nodes = self.settings["nodes"]
            for node in nodes:
                if node["guestOs"] == "Ubuntu":
                    nodeDeployer = NodeDeployer_Ubuntu(node)
                    nodeDeployer.create_node(get_free_port())
                elif node["guestOs"] == "Debian GNU/Linux":
                    nodeDeployer = NodeDeployer_Debian(node)
                    nodeDeployer.create_node(get_free_port())
                elif node["guestOs"] == "CentOS7":
                    nodeDeployer = NodeDeployer_CentOS7(node)
                    nodeDeployer.create_node(get_free_port())
                elif node["guestOs"] == "CentOS8":
                    nodeDeployer = NodeDeployer_CentOS8(node)
                    nodeDeployer.create_node(get_free_port())
                elif node["guestOs"] == "Alma8":
                    nodeDeployer = NodeDeployer_Alma8(node)
                    nodeDeployer.create_node(get_free_port())
                elif node["guestOs"] == "Alma9":
                    nodeDeployer = NodeDeployer_Alma9(node)
                    nodeDeployer.create_node(get_free_port())
                else:
                    pass
            # create start_cluster.sh
            script_path = clusterName + "/" + "start_cluster.sh"
            f_start_cluster = open(script_path, 'w')
            for node in nodes:
                f_start_cluster.write(
                    "cd {node_name} && ./start.sh && cd ..".format(node_name=node["name"]) + os.linesep)
            f_start_cluster.close()
            os.chmod(script_path, stat.S_IXGRP | stat.S_IXOTH | stat.S_IXUSR)
            return True


class Deployer_CentOS(Deployer_Ubuntu):
    def __init__(self, settings: dict):
        settings["qemubin"] = "/usr/libexec/qemu-kvm"
        IDeployer.__init__(self, settings)


class Deployer_Debian(Deployer_Ubuntu):
    pass


class NodeDeployer_Ubuntu:
    def __init__(self, settings: dict):
        self.node_settings = settings
        self.qemubin = settings["qemubin"]

    def create_node(self, port: int):
        """create a single node structure
            a node directory will be created inside the cluster folder.
            the folder will contain following files:
            1. a system virtual disk in qcow2 format
            2. a date disk ( if specified ) in qcow2 format
            3. a startup script with qemu command line in it
            4. a cloud-init sub-folder with a cloud-init iso for cloud image configurations.

            # cluster_name
            #   |- start_cluster.sh
            #   |- stop_cluster.sh
            #   |- node_name
            #   |    |- system.qcow2
            #   |    |- data.qcow2
            #   |    |- start.sh
            #   |    |- cloud-init
            #   |         |- meta-data
            #   |         |- user-data
            #   |         |- network-config
            #   |         |- cloud-init-provisioning.iso
        """
        clusterName = self.node_settings["clusterName"]
        imagePath = self.node_settings["imagePath"]
        nodeName = self.node_settings["name"]
        print("nodeName={}".format(nodeName))
        systemDiskSize = self.node_settings["systemDiskSize"]
        dataDiskSizes = self.node_settings["dataDiskSizes"]

        # download image if needed
        if parse.urlparse(imagePath).scheme in ('http', 'https'):
            localImage = download_to(imagePath)
        else:
            localImage = imagePath
        localImage = check_path(localImage)
        print("using {}".format(localImage))

        # create node dirs
        cloud_init_dir = clusterName + "/" + nodeName + "/" + "cloud-init"
        os.makedirs(cloud_init_dir, exist_ok=True)

        # generating mac address for vm
        mac = self.gen_mac("qemu")
        mac1 = self.gen_mac("qemu")
        mac2 = self.gen_mac("qemu")

        # prepare cloud-init config files
        self.write_meta(mac)
        self.write_netconf(mac)
        self.write_user(mac)

        # create cloud-init-provisioning.iso
        cmd = "cloud-localds -v --network-config={cloud_init_dir}/network-config {cloud_init_dir}/cloud-init-provisioning.iso {cloud_init_dir}/user-data {cloud_init_dir}/meta-data"
        cmd = cmd.format(cloud_init_dir=cloud_init_dir)
        print(cmd)
        exe(cmd)

        # prepare system.qcow2 and dataX.qcow2 (if defined)
        node_dir = clusterName + "/" + nodeName
        cmd = f"qemu-img create -f qcow2 -F qcow2 -b {localImage} {node_dir}/system.qcow2 {systemDiskSize}"
        exe(cmd)

        i = 1
        for size in dataDiskSizes:
            cmd = f"qemu-img create -f qcow2 {node_dir}/data{i}.qcow2 {size['size']}"
            i += 1
            exe(cmd)

        # prepare start.sh
        self.write_startup_script(mac, mac1, mac2, port)

    def gen_startup_script(self, mac: str, mac1: str, mac2: str, port: int):
        """
            the host must create 2 bridges before deploy qemu virtual machines:
            1. br0 for public access
            2. br1 for private data link 1
            3. br1 for private data link 2
        """
        script = """\
#!/usr/bin/bash

function create_tap
{{
    tapname=$1
    brname=$2
    [[ -z $tapname ]] && {{ >&2 echo "err: must specify a name for a tap device"; return 1; }}
    ip tuntap add dev $tapname mode tap
    ip link set dev $tapname mtu {mtu}
    ip link set dev $tapname up
    ip link set dev $tapname master $brname
}}

PUBLIC_NAME={node}-pub
PRIVATE_NAME={node}-pri
PRIVATE_NAME1={node}-pri1

[[ -z $PUBLIC_NAME ]] && {{ echo "err: VM name is missing in command line"; exit 1; }}
br=`ip link show dev br0 | wc -l`
[[ $br -eq 0 ]] && exit 1
tap=`ip link show dev tap$PUBLIC_NAME 2>/dev/null | wc -l`
[[ $tap -gt 0 ]] && {{ ip link del dev tap$PUBLIC_NAME; }}
create_tap tap$PUBLIC_NAME br0

[[ -z $PRIVATE_NAME ]] && {{ echo "err: VM name is missing in command line"; exit 1; }}
br=`ip link show dev br1 | wc -l`
[[ $br -eq 0 ]] && exit 1
tap=`ip link show dev tap$PRIVATE_NAME 2>/dev/null | wc -l`
[[ $tap -gt 0 ]] && {{ ip link del dev tap$PRIVATE_NAME; }}
create_tap tap$PRIVATE_NAME br1

[[ -z $PRIVATE_NAME1 ]] && {{ echo "err: VM name is missing in command line"; exit 1; }}
br=`ip link show dev br1 | wc -l`
[[ $br -eq 0 ]] && exit 1
tap=`ip link show dev tap$PRIVATE_NAME1 2>/dev/null | wc -l`
[[ $tap -gt 0 ]] && {{ ip link del dev tap$PRIVATE_NAME1; }}
create_tap tap$PRIVATE_NAME1 br1

{qemubin} \\
-display vnc=:0,to=100 \\
-machine pc,accel=kvm \\
-smp cpus={cpus} \\
-cpu host \\
-m {mem} \\
-drive file=system.qcow2,format=qcow2,if=none,id=D0,cache=none \\
-device virtio-blk-pci,drive=D0 \\
-drive file=cloud-init/cloud-init-provisioning.iso,media=cdrom \\
-netdev tap,id=mynet0,ifname=tap$PUBLIC_NAME,script=no,downscript=no \\
-device virtio-net-pci,netdev=mynet0,mac={mac} \\
-netdev tap,id=mynet1,ifname=tap$PRIVATE_NAME,script=no,downscript=no \\
-device virtio-net-pci,netdev=mynet1,mac={mac1} \\
-netdev tap,id=mynet2,ifname=tap$PRIVATE_NAME1,script=no,downscript=no \\
-device virtio-net-pci,netdev=mynet2,mac={mac2} \\
-boot c \\
""".format(node=self.node_settings["name"],
           qemubin=self.qemubin,
           cpus=self.node_settings["cpu"],
           mem=self.node_settings["mem"],
           mtu=self.node_settings["mtu"],
           mac=mac,
           mac1=mac1,
           mac2=mac2
           )

        i = 1
        dataDiskSizes = self.node_settings["dataDiskSizes"]
        clusterName = self.node_settings["clusterName"]
        nodeName = self.node_settings["name"]
        node_dir = clusterName + "/" + nodeName
        for size in dataDiskSizes:
            if not "type" in size:
                size["type"] = "virtio-blk-pci"
            script += """\
-drive file=data{n}.qcow2,format=qcow2,if=none,id=D{n},cache=none \\
-device {devtype},drive=D{n},serial=qemu_drive_{n} \\
""".format(disk_dir=node_dir, devtype=size["type"], n=i)
            i += 1

        script += """\
--daemonize
"""
        return script.encode('utf-8')

    def gen_meta(self, node_settings, mac: str) -> str:
        return ""

    def gen_user(self, node_settings, mac: str) -> str:
        """
            generate and return contents of user-data
            based on node settings from parameter.

            user-data content example:
            -------------------------
            #cloud-config

            hostname: node0
            fqdn: node0.chenp.net
            manage_etc_hosts: false

            ssh_pwauth: false
            disable_root: false

            users:
            - name: ubuntu
                home: /home/ubuntu
                shell: /bin/bash
                groups: sudo
                sudo: ALL=(ALL) NOPASSWD:ALL
                ssh-authorized-keys:
                - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAA ...
                - ssh-dss AAAAB3NzaC1kc3MAAACBANVJJTo ...
        """
        content = {
            "hostname": node_settings["name"],
            "fqdn": node_settings["name"] + "." + str.strip(node_settings["domainName"], "."),
            "manage_etc_hosts": False,
            "ssh_pwauth": False,
            "disable_root": False,
            "users": [
                {
                    "name": "ubuntu", "home": "/home/ubuntu", "shell": "/bin/bash", "groups": "sudo", "sudo": "ALL=(ALL) NOPASSWD:ALL",
                    "lock_passwd": False,
                    "passwd": "$6$j0iQN7y/xQ7RCfkU$NIJ1ONRVdJumo1KJCkpwlezoaZOqAE/0IR2UIwmh/S0vQKuDVzRQ3bf2uU3CUSBCF2BB.6W3b8yJMQ9cNaa8E0",
                    "ssh-authorized-keys": []
                },
                {
                    "name": "root",
                    "ssh-authorized-keys": []
                },
            ]
        }
        # add keys defined in settings
        for user in content["users"]:
            ssh_authorized_keys = user["ssh-authorized-keys"]
            for key in node_settings["authorized-keys"]:
                ssh_authorized_keys.append(key)
        return yaml.dump(content, width=1000)

    def gen_netconf(self, node_settings, mac: str) -> str:
        """
            generate a netplan file for cloud-init utilities.
            an example of netplan file content:
            ----------------------------------
            version: 2
            ethernets:
            id0:
                match:
                macaddress: '00:16:3e:5d:ca:c0'
                set-name: eth0
            eth0:
                addresses:
                - 10.1.0.60/24
                gateway4: 10.1.0.1
                nameservers:
                addresses:
                - 10.1.0.1
                search:
                - chenp.net
                mtu: 9000
        """
        content = {
            'version': 2,
            'ethernets': {
                'id0': {'match': {'macaddress': mac}, 'set-name': 'eth0'},
                'eth0': {
                    'addresses': [node_settings["ipAddress"]],
                    'gateway4': node_settings["gateway"],
                    'nameservers': {'addresses': [node_settings["nameserver"]], 'search': [str.strip(node_settings["domainName"], ".")]},
                    'mtu': node_settings["mtu"]
                }
            }
        }
        return yaml.safe_dump(content, width=1000)

    def gen_mac(self, qemu_or_xen):
        return random_mac(qemu_or_xen)

    def write_meta(self, mac: str):
        clusterName = self.node_settings["clusterName"]
        nodeName = self.node_settings["name"]

        cloud_init_dir = clusterName + "/" + nodeName + "/" + "cloud-init"
        meta_path = cloud_init_dir + "/" + "meta-data"

        f_meta = open(meta_path, 'w')
        f_meta.write(self.gen_meta(self.node_settings, mac))
        f_meta.close()

    def write_netconf(self, mac: str):
        clusterName = self.node_settings["clusterName"]
        nodeName = self.node_settings["name"]

        cloud_init_dir = clusterName + "/" + nodeName + "/" + "cloud-init"
        netconf_path = cloud_init_dir + "/" + "network-config"

        f_netconf = open(netconf_path, 'w')
        f_netconf.write(self.gen_netconf(self.node_settings, mac))
        f_netconf.close()

    def write_user(self, mac: str):
        clusterName = self.node_settings["clusterName"]
        nodeName = self.node_settings["name"]

        cloud_init_dir = clusterName + "/" + nodeName + "/" + "cloud-init"
        user_path = cloud_init_dir + "/" + "user-data"

        f_user = open(user_path, 'w')
        f_user.write("#cloud-config" + os.linesep + os.linesep)
        f_user.write(self.gen_user(self.node_settings, mac))
        f_user.close()

    def write_startup_script(self, mac, mac1, mac2, port):
        # prepare start.sh
        clusterName = self.node_settings["clusterName"]
        nodeName = self.node_settings["name"]

        node_dir = clusterName + "/" + nodeName
        start_script_path = node_dir + "/" + "start.sh"
        f_startup_script = open(start_script_path, 'wb')
        f_startup_script.write(self.gen_startup_script(mac, mac1, mac2, port))
        f_startup_script.close()
        os.chmod(start_script_path, stat.S_IXGRP | stat.S_IXOTH | stat.S_IXUSR)


class NodeDeployer_CentOS7(NodeDeployer_Ubuntu):
    pass


class NodeDeployer_CentOS8(NodeDeployer_CentOS7):
    def gen_user(self, node_settings, mac: str) -> str:
        content = super().gen_user(node_settings, mac) + os.linesep
        content += 'bootcmd:' + os.linesep + \
            '    - nmcli device connect eth0' + os.linesep
        return content

    def gen_meta(self, node_settings, mac: str):
        """
            in file meta-data:
            network-interfaces: |
                iface eth0 inet static
                address 192.168.122.8
                network 192.168.122.0
                netmask 255.255.255.0
                broadcast 192.168.1.255
                gateway 192.168.122.1
        """
        content = 'network-interfaces: |' + "\n" + \
            '    iface eth0 inet static' + "\n" + \
            '    address {}'.format(node_settings["ipAddress"]) + "\n" + \
            '    netmask 255.255.255.0' + "\n" + \
            '    gateway {}'.format(
                node_settings["gateway"]) + os.linesep
        return content

    def gen_netconf(self, node_settings, mac: str) -> str:
        return ""


class NodeDeployer_Debian(NodeDeployer_Ubuntu):
    pass


class NodeDeployer_Alma8(NodeDeployer_CentOS8):
    pass


class NodeDeployer_Alma9(NodeDeployer_Alma8):
    pass


def distro_name() -> str:
    v = distro.info()
    return v["id"]


def cmd_deploy():
    # get config file path from command line
    settings_for_apply = {}
    apply_handleopts(settings_for_apply)
    configfile = settings_for_apply["configfile"]

    # read cluster settings from config file
    if os.path.exists(configfile):
        cluster_settings = yaml.safe_load(open(configfile).read())

    # find host os distro
    dist = distro_name()
    if dist == "Ubuntu":
        deployer = Deployer_Ubuntu(cluster_settings)
    elif dist in ["CentOS Stream", "rocky"]:
        deployer = Deployer_CentOS(cluster_settings)
    elif dist == "Debian GNU/Linux":
        deployer = Deployer_Debian(cluster_settings)
    else:
        usage("platform '{}' not implemented yet.".format(dist))

    # deploy cluster
    deployer.deploy()


if __name__ == "__main__":
    load_settings()

    command = sys.argv[1]
    # argv[1] must be one of:
    if command == 'deploy':
        cmd_deploy()
    else:
        usage('command "{}" not recognized.'.format(command))
