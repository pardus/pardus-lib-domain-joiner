import configparser
import os
import shutil
import subprocess


def set_hostname(comp_name):
    backup_config_file("/etc/hostname", "/etc/hostname.old")
    update_hosts_file(comp_name)
    subprocess.call(["hostnamectl", "hostname", comp_name])
    print("Changed hostname: ", comp_name)


def restore_hostname():
    if os.path.isfile("/etc/hostname.old"):
        with open("/etc/hostname.old", "r") as f:
            comp_name = f.read()
        subprocess.call(["hostnamectl", "hostname", comp_name])
        print("Restored hostname file: ", comp_name)
        restore_config_file("/etc/hosts.old", "/etc/hosts")


def start_sssd_service():
    print("Starting sssd service...")
    subprocess.run(["systemctl", "stop", "winbind.service"], capture_output=True)
    subprocess.run(["systemctl", "disable", "winbind.service"], capture_output=True)
    subprocess.run(["systemctl", "start", "sssd.service"], capture_output=True)
    subprocess.run(["systemctl", "enable", "sssd.service"], capture_output=True)


def start_winbind_service():
    print("Starting winbind service...")
    subprocess.run(["systemctl", "stop", "sssd.service"], capture_output=True)
    subprocess.run(["systemctl", "disable", "sssd.service"], capture_output=True)
    subprocess.run(["systemctl", "start", "winbind.service"], capture_output=True)
    subprocess.run(["systemctl", "enable", "winbind.service"], capture_output=True)


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

            # Remove old backup to prevent restoring it again
            os.remove(backup_file)

        except Exception as e:
            print(f"An error occurred while restoring {source_file}. Error: {e}")
    else:
        print(f"There is no such file: {backup_file}.")


def update_hostname_file(comp_name, domain=None):
    # to check file /etc/hostname
    hostname_file = "/etc/hostname"
    hostname_file_backup = "/etc/hostname.old"
    backup_config_file(hostname_file, hostname_file_backup)

    full_hostname = f"{comp_name}.{domain}" if domain else comp_name

    with open(hostname_file, "r") as file:
        current_hostname = file.readline().strip()
        print("Checking /etc/hostname file...")
        if full_hostname not in current_hostname:
            print("Added domain name to /etc/hostname file")
            with open(hostname_file, "w") as file:
                new_hostname = f"{full_hostname}"
                file.write(new_hostname)
        else:
            print("Done")


def update_hosts_file(comp_name, domain=None):
    # to check file /etc/hosts
    hosts_file = "/etc/hosts"
    hosts_file_backup = "/etc/hosts.old"

    if not os.path.isfile(hosts_file):
        print("/etc/hosts not found.")
        return False

    backup_config_file(hosts_file, hosts_file_backup)

    with open(hosts_file, "r") as file:
        lines = file.readlines()

    print("Checking /etc/hosts file...")

    new_hosts_file = []
    updated = False

    full_hostname = f"{comp_name}.{domain}" if domain else comp_name
    new_entry = (
        f"127.0.1.1 {full_hostname} {comp_name}" if domain else f"127.0.1.1 {comp_name}"
    )

    for line in lines:
        if line.strip().startswith("127.0.1.1"):
            if full_hostname not in line:
                line = f"{new_entry}\n"
            updated = True
        new_hosts_file.append(line)

    if not updated:
        new_hosts_file.append(f"{new_entry}\n")

    with open(hosts_file, "w") as file:
        file.writelines(new_hosts_file)

    if updated:
        print("Done")
    else:
        print("Added hostname to /etc/hosts file")


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

    os.chmod(file, 0o755)


def update_samba_conf_for_sssd(domain):
    smb_file = "/etc/samba/smb.conf"
    smb_file_backup = "/etc/samba/smb.conf.old"
    backup_config_file(smb_file, smb_file_backup)
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
    print("Updating /etc/samba/smb.conf file...")
    rewrite_conf(smb_file, samba_settings)
    print("Updated /etc/samba/smb.conf file...")


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
    print("Updating /etc/sssd/sssd.conf file...")
    rewrite_conf(sssd_file, sssd_settings)
    os.chmod(sssd_file, 600)
    subprocess.call(["systemctl", "restart", "sssd.service"])
    print("Updated /etc/sssd/sssd.conf file...")


def update_samba_conf_for_winbind(domain, workgroup):
    smb_file = "/etc/samba/smb.conf"
    smb_file_backup = "/etc/samba/smb.conf.old"
    backup_config_file(smb_file, smb_file_backup)

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
    print("Updating /etc/samba/smb.conf file for winbind...")
    rewrite_conf(smb_file, samba_settings)
    print("Updated /etc/samba/smb.conf file for winbind...")


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

    print("Updating /etc/nsswitch.conf file for winbind...")
    with open(nsswitch_file, "w") as file:
        file.writelines(new_lines)
    print("Updated /etc/nsswitch.conf file for winbind...")
