import os
import subprocess
import sys
import apt

from pardus_domain_core import domain_joiner_realmd
from pardus_domain_core import domain_joiner_winbind
from pardus_domain_core import config_manager
from pardus_domain_core import update_krb5_config

from locale import gettext as _


def isinstalled(packagename):
    try:
        cache = apt.Cache()
        cache.open()
        package = cache[packagename]
    except Exception as e:
        print("{}".format(e))
        return False
    return package.is_installed


def update():
    subprocess.call(
        ["apt", "update", "-o", "APT::Status-Fd=2"],
        env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
    )


def install(package_list):
    for package in package_list:
        subprocess.call(
            ["apt", "install", package, "-yq", "-o", "APT::Status-Fd=2"],
            env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
        )


def check_and_install_packages(package_list):
    not_installed = []

    for package in package_list:
        if not isinstalled(package):
            print(_("{} is not installed.").format(package))
            not_installed.append(package)
        else:
            print(_("{} is installed.").format(package))

    if not_installed:
        print(_("Required packages are installing."))
        # to update
        update()
        # install packages
        install(package_list)

        # re-check not installed packages
        for ni_package in not_installed:
            if isinstalled(ni_package):
                print(_("{} is now installed.").format(ni_package))
            else:
                print(_("{} failed to installed.").format(ni_package))
    else:
        print(_("All required packages are already installed."))


def discover_domain(domain):
    result = subprocess.run(["nslookup", domain], capture_output=True, text=True)

    output = result.stdout
    error = result.stderr

    if "can't find" in output or "non-existent domain" in output:
        print("Domain name not found!")
    elif result.returncode != 0:
        print("An error occured: ", error)
    else:
        print("Domain discovered:\n", output.strip().split("\n"))


def fail_and_exit(msg):
    print(_(msg), file=sys.stdout)
    config_manager.restore_hostname()
    sys.exit(1)


def restore_config_file(restore_files):
    for backup, original in restore_files.items():
        if os.path.exists(backup):
            config_manager.restore_config_file(backup, original)

def check_ouaddress(ouaddress, domain):
    if ouaddress is None:
        fulldn = ", dc=" + domain.replace(".",", dc=")
        ouaddress = "cn=Computers" + fulldn
        return ouaddress
    return ouaddress

def handle_realmd_join(comp_name, domain, user, passwd, ouaddress, smb_settings):
    if not os.path.isfile("/etc/krb5.conf"):
        fail_and_exit("krb5.conf not found. Required packages might be missing.")

    try:
        result = domain_joiner_realmd.discover(domain)
        if result:
            print(_("Domain discovered..."))
    except subprocess.CalledProcessError as e:
        print(_("Error discovering domain. Exit Code:"), e.returncode)
        fail_and_exit("Domain discovery failed.")

    try:
        # print("domain:", domain)
        print(_("Joining the domain..."))
        messages = domain_joiner_realmd.join(domain, user, passwd, ouaddress)
        client = f"{user}@{domain.upper()}"


        if "Preauthentication failed" in messages:
            fail_and_exit("Preauthentication failed!")
        elif f"Client '{client}' not found in Kerberos database" in messages:
            fail_and_exit(f"Client '{client}' not found in Kerberos database!")
        elif "The organizational unit does not exist" in messages:
            fail_and_exit("The organizational unit does not exist.")
        elif "not in the desired organizational unit" in messages:
            fail_and_exit("Not in the desired organizational unit.")
        elif "Successfully enrolled machine in realm" in messages:
            config_manager.update_hostname_file(comp_name, domain)
            config_manager.update_hosts_file(comp_name, domain)

            if smb_settings:
                config_manager.update_samba_conf_for_sssd(domain)

            config_manager.update_sssd_conf(domain)

            subprocess.call(
                ["pam-auth-update", "--enable", "pardus-pam-config"],
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
            )

            print(_("This computer has been successfully added to the domain."))
        else:
            print(_("This computer cannot be joined to the domain!"))
            restore_files = {
                "/etc/hosts.old": "/etc/hosts",
                "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
                "/etc/sssd/sssd.conf.old": "/etc/sssd/sssd.conf",
            }
            restore_config_file(restore_files)
            fail_and_exit("This computer cannot be joined to the domain!")

    except subprocess.CalledProcessError as e:
        print(_("Error while joining domain. Exit Code:"), e.stderr)
        restore_files = {
            "/etc/hosts.old": "/etc/hosts",
            "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
            "/etc/sssd/sssd.conf.old": "/etc/sssd/sssd.conf",
        }
        restore_config_file(restore_files)
        fail_and_exit("Error while joining domain.")
    except Exception as e:
        print("Error: ", e)
        restore_files = {
            "/etc/hosts.old": "/etc/hosts",
            "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
            "/etc/sssd/sssd.conf.old": "/etc/sssd/sssd.conf",
        }
        restore_config_file(restore_files)
        fail_and_exit(f"Error: {e}")

def handle_winbind_join(comp_name, domain, user, passwd, ouaddress):
    if not os.path.isfile("/etc/krb5.conf"):
        fail_and_exit("krb5.conf not found. Required packages might be missing.")

    try:
        print(_("Updating /etc/krb5.conf file..."))
        update_krb5_config.update_krb5_conf(domain)
        print(_("Updated /etc/krb5.conf file..."))
        config_manager.update_samba_conf_for_winbind(domain)

        try:
            result = domain_joiner_winbind.discover()
            if result:
                print(_("Domain discovered..."))
        except subprocess.CalledProcessError as e:
            print(_("Error discovering domain. Exit Code:"), e.returncode)
            restore_files = {
                "/etc/krb5.conf.old": "/etc/krb5.conf",
                "/etc/samba/smb.conf.old": "/etc/samba/smb.conf"
            }
            restore_config_file(restore_files)
            fail_and_exit("Domain discovery failed.")
        
        config_manager.update_nsswitch_conf()
        # domain_user = f"{user}@{domain}"
        # result = subprocess.run(["kinit", domain_user], capture_output=True)
        # print("result:",result, "\n", result.returncode)
        config_manager.update_hostname_file(comp_name, domain)
        config_manager.update_hosts_file(comp_name, domain)
        msg = domain_joiner_winbind.join(user, passwd, ouaddress)
        print("msg: ", msg)

        messages = msg.stdout.split("\n")[-2]

        if "a bad username or authentication information" in messages:
            restore_files = {
                "/etc/hosts.old": "/etc/hosts",
                "/etc/krb5.conf.old": "/etc/krb5.conf",
                "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
                "/etc/nsswitch.conf.old": "/etc/nsswitch.conf"
            }
            restore_config_file(restore_files)
            fail_and_exit("Preauthentication failed!")
        elif "Joined" in messages:
            subprocess.run(
                ["systemctl", "restart", "smbd", "nmbd", "winbind"], capture_output=True
            )

            result = domain_joiner_winbind.domain_info()
            
            if result:
                print(_("This computer has been successfully added to the domain."))
            else:
                print(_("This computer cannot be joined to the domain!"))
                restore_files = {
                    "/etc/krb5.conf.old": "/etc/krb5.conf",
                    "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
                    "/etc/nsswitch.conf.old": "/etc/nsswitch.conf",
                    "/etc/hosts.old": "/etc/hosts"
                }
                restore_config_file(restore_files)
                fail_and_exit("This computer cannot be joined to the domain!")
    except subprocess.CalledProcessError as e:
        print(_("Error while joining domain. Exit Code:"), e.stderr)
        restore_files = {
            "/etc/krb5.conf.old": "/etc/krb5.conf",
            "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
            "/etc/nsswitch.conf.old": "/etc/nsswitch.conf",
            "/etc/hosts.old": "/etc/hosts"
        }
        restore_config_file(restore_files)
        fail_and_exit(f"Error while joining domain. Exit Code: {e.stderr}")
    except Exception as e:
        print("Error: ", e)
        restore_files = {
            "/etc/krb5.conf.old": "/etc/krb5.conf",
            "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
            "/etc/nsswitch.conf.old": "/etc/nsswitch.conf",
            "/etc/hosts.old": "/etc/hosts"
        }
        restore_config_file(restore_files)
        fail_and_exit(f"Error: {e}")


def join(
    comp_name, domain, user, passwd, ouaddress=None, smb_settings=False, realmd=None, winbind=None
):
    try:
        ouaddress = check_ouaddress(ouaddress, domain)
        if realmd:
            # required packages
            sssd_pkg_list = [
                "krb5-user",
                "samba",
                "sssd",
                "libsss-sudo",
                "realmd",
                "packagekit",
                "adcli",
                "sssd-tools",
                "cifs-utils",
                "smbclient",
            ]
            check_and_install_packages(sssd_pkg_list)
            handle_realmd_join(comp_name, domain, user, passwd, ouaddress, smb_settings)
        elif winbind:
            winbind_pkg_list = [
                "samba",
                "smbclient",
                "krb5-user",
                "winbind",
                "libnss-winbind",
                "libpam-winbind",
            ]
            check_and_install_packages(winbind_pkg_list)

            handle_winbind_join(comp_name, domain, user, passwd, ouaddress)
        else:
            print(
                _(
                    "No domain join method selected. Please specify either realmd or winbind."
                )
            )
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(_("An error occurred during the join process:"), e.stderr)


def leave(realmd=None, winbind=None, user=None, password=None):
    if realmd:
        domain_joiner_realmd.leave()
        restore_files = {
            "/etc/hosts.old": "/etc/hosts",
            "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
            "/etc/sssd/sssd.conf.old": "/etc/sssd/sssd.conf",
        }
        restore_config_file(restore_files)
        config_manager.restore_hostname()

    elif winbind:
        domain_joiner_winbind.leave(user, password)
        restore_files = {
            "/etc/hosts.old": "/etc/hosts",
            "/etc/krb5.conf.old": "/etc/krb5.conf",
            "/etc/nsswitch.conf.old": "/etc/nsswitch.conf",
            "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
        }
        restore_config_file(restore_files)
        config_manager.restore_hostname()

def list(realmd=None, winbind=None):
    if realmd:
        process = domain_joiner_realmd.list_realm()
        if process.returncode == 0:
            realm_name = process.stdout.decode("utf-8").split("\n")[0]
            return realm_name
    elif winbind:
        domain_info = domain_joiner_winbind.domain_info()
        if domain_info.returncode == 0:
            process = domain_joiner_winbind.discover()
            lines = process.stdout.splitlines()
            for line in lines:
                if line.startswith("Realm"):
                    realm_name = line.split(":")[1].strip()
                    return realm_name
