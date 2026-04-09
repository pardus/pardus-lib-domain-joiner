import configparser
import os
import shutil
import subprocess
import re
from datetime import datetime
from logger import get_logger
import locale
from locale import gettext as _

# Development: ../locale, Production: /usr/share/locale
localedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../locale')
if not os.path.exists(localedir):
    localedir = '/usr/share/locale'

SYSTEM_LANGUAGE = os.environ.get("LANG")
locale.setlocale(locale.LC_ALL, os.environ.get("LANG"))

locale.bindtextdomain('pardus-lib-domain-joiner', localedir)
locale.textdomain('pardus-lib-domain-joiner')

# Logger
logger = get_logger("config_manager")

# to backup files
backup_dir = "/usr/share/pardus_domain_joiner/backups"


def valid_hostname(hostname):
    pattern = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
    return bool(pattern.match(hostname))

def set_hostname(comp_name):
    if valid_hostname(comp_name):
        backup_config_file("/etc/hostname", "hostname")
        update_hosts_file(comp_name)
        subprocess.call(["hostnamectl", "hostname", comp_name])
        #print(_("Changed hostname: "), comp_name)
        logger.info(_("Changed hostname: %s"), comp_name)
    else:
        #print(_("ERROR: You entered an invalid hostname."))
        logger.error(_("ERROR: You entered an invalid hostname."))


def restore_hostname():
    backup_hostname = os.path.join(backup_dir, "hostname")
    if os.path.exists(backup_hostname):
        with open(backup_hostname, "r") as f:
            comp_name = f.read().strip()
        subprocess.call(["hostnamectl", "hostname", comp_name])
        #print(_("Restored hostname file: "), comp_name)
        logger.info(_("Restored hostname file: %s"), comp_name)
        restore_config_file("hosts", "/etc/hosts")
        restore_config_file("hostname", "/etc/hostname")
    else:
        logger.warning(_("No backup found for hostname."))


def start_sssd_service():
    #print(_("Starting sssd service..."))
    logger.info(_("Starting sssd service..."))
    subprocess.run(["systemctl", "stop", "winbind.service"], capture_output=True)
    subprocess.run(["systemctl", "disable", "winbind.service"], capture_output=True)
    subprocess.run(["systemctl", "start", "sssd.service"], capture_output=True)
    subprocess.run(["systemctl", "enable", "sssd.service"], capture_output=True)


def start_winbind_service():
    #print(_("Starting winbind service..."))
    logger.info(_("Starting winbind service..."))
    subprocess.run(["systemctl", "stop", "sssd.service"], capture_output=True)
    subprocess.run(["systemctl", "disable", "sssd.service"], capture_output=True)
    subprocess.run(["systemctl", "start", "winbind.service"], capture_output=True)
    subprocess.run(["systemctl", "enable", "winbind.service"], capture_output=True)


# backup config files before editing them
def backup_config_file(source_file, backup_name):
    # backup_time = datetime.now().strftime("%y.%m.%d-%H.%M")
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, backup_name)
    if os.path.exists(source_file):
        try:
            shutil.copy2(source_file, backup_file)
            #print(f"{source_file} backed up.")
            logger.info(_("%s backed up."), source_file)
        except Exception as e:
            #print(_("An error occurred while backing up {}. Error: {}").format(source_file, e))
            logger.exception(_("An error occurred while backing up %s. Error: %s"), source_file, e)
    else:
        #print(_("There is no such file: {}.").format(source_file))
        logger.warning(_("There is no such file: %s."), source_file)


"""def get_latest_backup(target_file):
    all_files = os.listdir(backup_dir)
    matching_backups = [
        f for f in all_files
        if f.endswith("-" + target_file)
    ]

    #print("matching_backups", matching_backups)

    if not matching_backups:
        return None

    matching_backups.sort()
    latest_backup_name = matching_backups[-1]
    latest_backup_path = os.path.join(backup_dir, latest_backup_name)

    return latest_backup_path"""


# to restore edited config files
def restore_config_file(backup_name, source_file):
    backup_file = os.path.join(backup_dir, backup_name)
    if not backup_file or not os.path.exists(backup_file):
        #print(_("No backup found for "), backup_file)
        logger.warning(_("No backup found for %s."), backup_file)
        return

    if os.path.exists(source_file):
        try:
            shutil.copy2(backup_file, source_file)
            #print(_("{} has been restored from backup.").format(source_file))
            logger.info(_("%s has been restored from backup."), source_file)

            # Remove old backup to prevent restoring it again
            os.remove(backup_file)

        except Exception as e:
            #print(_("An error occurred while restoring {}. Error: {}").format(source_file, e))
            logger.exception(_("An error occurred while restoring %s. Error: %s"), source_file, e)
    else:
        #print(_("There is no such file: {}.").format(backup_file))
        logger.warning(_("There is no such file: %s."), backup_file)


def update_hostname_file(comp_name, domain=None):
    # to check file /etc/hostname
    hostname_file = "/etc/hostname"
    backup_config_file(hostname_file, "hostname")

    full_hostname = f"{comp_name}.{domain}" if domain else comp_name

    with open(hostname_file, "r") as file:
        current_hostname = file.readline().strip()
        #print(_("Checking /etc/hostname file..."))
        logger.info(_("Checking /etc/hostname file..."))
        if full_hostname not in current_hostname:
            subprocess.call(["hostnamectl", "set-hostname", full_hostname])
            #print(_("Added domain name to /etc/hostname file"))
            logger.info(_("Added domain name to /etc/hostname file"))
            """with open(hostname_file, "w") as file:
                new_hostname = f"{full_hostname}"
                file.write(new_hostname)"""
        else:
            #print(_("Done"))
            logger.info(_("Done"))


def update_hosts_file(comp_name, domain=None):
    # to check file /etc/hosts
    hosts_file = "/etc/hosts"

    if not os.path.isfile(hosts_file):
        #print(_("/etc/hosts not found."))
        logger.error(_("/etc/hosts not found."))
        return False

    backup_config_file(hosts_file, "hosts")

    with open(hosts_file, "r") as file:
        lines = file.readlines()

    #print(_("Checking /etc/hosts file..."))
    logger.info(_("Checking /etc/hosts file..."))

    new_hosts_file = []
    updated = False

    full_hostname = f"{comp_name}.{domain}" if domain else comp_name
    new_entry = (
        f"127.0.1.1 {full_hostname} {comp_name}" if domain else f"127.0.1.1 {comp_name}"
    )

    for line in lines:
        if line.strip().startswith("127.0.1.1"):
            if full_hostname != line:
                line = f"{new_entry}\n"
            updated = True
        new_hosts_file.append(line)

    if not updated:
        new_hosts_file.append(f"{new_entry}\n")

    with open(hosts_file, "w") as file:
        file.writelines(new_hosts_file)

    if updated:
        #print(_("Done"))
        logger.info(_("Done"))
    else:
        #print(_("Added hostname to /etc/hosts file"))
        logger.info(_("Added hostname to /etc/hosts file"))


def rewrite_conf(file, settings):
    config = configparser.RawConfigParser(
        strict=False  # strict=False, ignores duplicated options (and other things)
    )
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
    backup_config_file(smb_file, "samba-sssd")
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
    #print(_("Updating /etc/samba/smb.conf file..."))
    logger.info(_("Updating /etc/samba/smb.conf file..."))
    rewrite_conf(smb_file, samba_settings)
    #print(_("Updated /etc/samba/smb.conf file..."))
    logger.info(_("Updated /etc/samba/smb.conf file..."))


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
    #print(_("Updating /etc/sssd/sssd.conf file..."))
    logger.info(_("Updating /etc/sssd/sssd.conf file..."))
    rewrite_conf(sssd_file, sssd_settings)
    os.chmod(sssd_file, 0o600)  # -rw------
    os.chown(sssd_file, 0, 0)  # root:root
    subprocess.call(["systemctl", "restart", "sssd.service"])
    #print(_("Updated /etc/sssd/sssd.conf file..."))
    logger.info(_("Updated /etc/sssd/sssd.conf file..."))


def update_samba_conf_for_winbind(domain, workgroup):
    smb_file = "/etc/samba/smb.conf"
    backup_config_file(smb_file, "samba-winbind")

    samba_settings = {
        "global": {
            "realm": domain,
            "workgroup": workgroup,
            "security": "ads",
            "domain logons": "no",
            "password server": domain,
            "template homedir": "/home/%D/%U",
            "template shell": "/bin/bash",
            "winbind enum groups": "yes",
            "winbind enum users": "yes",
            "winbind use default domain": "yes",
            "domain master": "no",
            "local master": "no",
            "prefered master": "no",
            "os level": "0",
            "idmap config *:backend": "tdb",
            "idmap config *:range": "11000-20000",
            "idmap config DOMAIN:backend": "rid",
            "idmap config DOMAIN:range": "10000000-19000000",
            "idmap uid = 10000-20000 idmap gid": "10000-20000",
            "client use spnego": "yes",
            "client ntlmv2 auth": "yes",
            "encrypt passwords": "yes",
            "winbind use default domain": "yes",
            "restrict anonymous": "2",
        },
    }
    #print(_("Updating /etc/samba/smb.conf file for winbind..."))
    logger.info(_("Updating /etc/samba/smb.conf file for winbind..."))
    rewrite_conf(smb_file, samba_settings)
    os.chmod(smb_file, 0o755)
    #print(_("Updated /etc/samba/smb.conf file for winbind..."))
    logger.info(_("Updated /etc/samba/smb.conf file for winbind..."))


def update_nsswitch_conf():
    nsswitch_file = "/etc/nsswitch.conf"
    backup_config_file(nsswitch_file, "nsswitch")

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

    #print(_("Updating /etc/nsswitch.conf file for winbind..."))
    logger.info(_("Updating /etc/nsswitch.conf file for winbind..."))
    with open(nsswitch_file, "w") as file:
        file.writelines(new_lines)
    #print(_("Updated /etc/nsswitch.conf file for winbind..."))
    logger.info(_("Updated /etc/nsswitch.conf file for winbind..."))
