import configparser
import os
import shutil
import subprocess

from locale import gettext as _


def set_hostname(comp_name):
    backup_config_file("/etc/hostname", "/etc/hostname.old")
    subprocess.call(["hostnamectl", "hostname", comp_name])
    print(_("Changed hostname: "), comp_name)


def restore_hostname():
    if os.path.isfile("/etc/hostname.old"):
        with open("/etc/hostname.old") as f:
            comp_name = f.read()
        subprocess.call(["hostnamectl", "hostname", comp_name])
        print(_("Restored hostname: "), comp_name)
    else:
        print(_("Failed the restore hostname."))


# backup config files before editing them
def backup_config_file(source_file, backup_file):
    if os.path.exists(source_file):
        try:
            shutil.copy2(source_file, backup_file)
            print(f"{source_file} backed up.")
        except Exception as e:
            print(f"An error occurred while backing up {source_file}. Error: {e}")
    else:
        print(f"There is no such file: {source_file}.")


# to restore edited config files
def restore_config_file(backup_file, source_file):
    if os.path.exists(source_file):
        try:
            shutil.copy2(backup_file, source_file)
            print(f"{source_file} has been restored from backup.")
        except Exception as e:
            print(f"An error occurred while restoring {source_file}. Error: {e}")
    else:
        print(f"There is no such file: {backup_file}.")


def update_hostname_file(comp_name, domain):
    # to check file /etc/hostname
    hostname_file = "/etc/hostname"
    hostname_file_backup = "/etc/hostname.old"
    backup_config_file(hostname_file, hostname_file_backup)
    with open(hostname_file, "r") as file:
        current_hostname = file.readline().strip()
        print(_("Checking /etc/hostname file..."))
        if comp_name + "." + domain not in current_hostname:
            print(_("Added domain name to /etc/hostname file"))
            with open(hostname_file, "w") as file:
                new_hostname = "{}.{}".format(comp_name, domain)
                file.write(new_hostname)
        else:
            print(_("Done"))


def update_hosts_file(comp_name, domain):
    # to check file /etc/hosts
    hosts_file = "/etc/hosts"
    hosts_file_backup = "/etc/hosts.old"
    backup_config_file(hosts_file, hosts_file_backup)
    with open(hosts_file, "r") as file:
        lines = file.readlines()
    print(_("Checking /etc/hosts file..."))
    new_hosts_file = []
    domain_exists = False

    for line in lines:
        if line.strip().startswith("127.0.1.1"):
            if f"{comp_name}.{domain}" not in line:
                line = f"127.0.1.1 {comp_name}.{domain} {comp_name}\n"
            domain_exists = True
        new_hosts_file.append(line)

    if not domain_exists:
        new_hosts_file.append(f"127.0.1.1 {comp_name}.{domain} {comp_name}\n")

    with open(hosts_file, "w") as file:
        file.writelines(new_hosts_file)

    if domain_exists:
        print(_("Done"))
    else:
        print(_("Added domain name to /etc/hosts file"))


def rewrite_conf(file, settings):
    config = configparser.RawConfigParser()
    config.optionxform = str  # This prevents it from converting keys to lowercase

    if os.path.exists(file):
        config.read(file)

    for section, options in settings.items():
        if not config.has_section(section):
            config.add_section(section)
        for key, value in options.items():
            config.set(section, key, value)

    with open(file, "w") as configfile:
        config.write(configfile)


def update_samba_conf_for_sssd(domain):
    smb_file = "/etc/samba/smb.conf"
    smb_file_backup = "/etc/samba/smb.conf.old"
    backup_config_file(smb_file,smb_file_backup)
    samba_settings = {
        "global": {
            "unix charset": "UTF-8",
            "workgroup": domain.split(".")[0].upper(),
            "client signing": "yes",
            "client use spnego": "yes",
            "dedicated keytab file": "/etc/krb5.keytab",
            "kerberos method": "secrets and keytab",
            "realm": domain,
            "dns proxy": "no",
            "map to guest": "Bad User",
            "log file": "/var/log/samba/log.%m",
            "max log size": 1000,
            "syslog": 0,
        },
    }
    print(_("Updating /etc/samba/smb.conf file..."))
    rewrite_conf(smb_file, samba_settings)
    print(_("Updated /etc/samba/smb.conf file..."))


def update_sssd_conf(domain):
    sssd_file = "/etc/sssd/sssd.conf"
    sssd_settings = {
        "sssd": {
            "domains": domain,
            "config_file_version": 2,
            "services": "nss, pam",
        },
        f"domain/{domain}": {
            "default_shell": "/bin/bash",
            "krb5_store_password_if_offline": True,
            "cache_credentials": True,
            "krb5_realm": domain,
            "realmd_tags": "manages-system joined-with-adcli",
            "id_provider": "ad",
            "fallback_homedir": "/home/%u@%d",
            "ad_domain": domain.upper(),
            "use_fully_qualified_names": False,
            "ldap_id_mapping": True,
            "access_provider": "ad",
            "ad_gpo_access_control": "permissive",
            "ad_gpo_ignore_unreadable": True,
        },
    }
    print(_("Updating /etc/sssd/sssd.conf file..."))
    rewrite_conf(sssd_file, sssd_settings)
    os.chmod(sssd_file, 600)
    subprocess.call(["systemctl", "restart ", "sssd"])
    print(_("Updated /etc/sssd/sssd.conf file..."))


def update_samba_conf_for_winbind(domain):
    smb_file = "/etc/samba/smb.conf"
    smb_file_backup = "/etc/samba/smb.conf.old"
    backup_config_file(smb_file,smb_file_backup)
    samba_settings = {
        "global": {
            "realm" : domain,
            "workgroup" : domain.split(".")[0].upper(),
            "security" : "ads",
            "domain logons" : "no",
            "password server" : domain,
            "template homedir" : "/home/%D/%U",
            "template shell" : "/bin/bash",
            "winbind enum groups" : "yes",
            "winbind enum users" : "yes",
            "winbind use default domain" : "yes",
            "domain master" : "no",
            "local master" : "no",
            "prefered master" : "no",
            "os level" : "0",
            "idmap config *:backend" : "tdb",
            "idmap config *:range" : "11000-20000",
            "idmap config DOMAIN:backend" : "rid",
            "idmap config DOMAIN:range":"10000000-19000000",
            "idmap uid = 10000-20000 idmap gid" : "10000-20000",
            "client use spnego" : "yes",
            "client ntlmv2 auth" : "yes",
            "encrypt passwords" : "yes", 
            "winbind use default domain" : "yes",
            "restrict anonymous" : "2"
        },
    }
    print(_("Updating /etc/samba/smb.conf file for winbind..."))
    rewrite_conf(smb_file, samba_settings)
    print(_("Updated /etc/samba/smb.conf file for winbind..."))


def update_nsswitch_conf():
    nsswitch_file = "/etc/nsswitch.conf"
    nsswitch_file_backup = "/etc/nsswitch.conf.old"
    backup_config_file(nsswitch_file, nsswitch_file_backup)

    keys = ["passwd", "group", "shadow"]

    with open(nsswitch_file, "r") as file:
        lines = file.readlines()
    
    new_lines = []

    for line in lines:
        if line.strip().startswith("#") or ":" not in line:
            new_lines.append(line)
            continue
        key, value = line.split(":", 1)
        key = key.strip()

        if key in keys:
            items = value.strip().split()

            if "winbind" not in items:
                items.append("winbind")
            new_line = f"{key}:\t{' '.join(items)}\n"
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    

    print(_("Updating /etc/nsswitch.conf file for winbind..."))    
    with open(nsswitch_file, "w") as file:
        file.writelines(new_lines)
    print(_("Updated /etc/nsswitch.conf file for winbind..."))
