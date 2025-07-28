import os
import subprocess
import sys

from pardus_domain_joiner import domain_joiner_realmd
from pardus_domain_joiner import domain_joiner_winbind
from pardus_domain_joiner import config_manager
from pardus_domain_joiner import update_krb5_config


def discover_domain(domain):
    process = subprocess.run(["nslookup", domain], capture_output=True, text=True)

    if process.returncode == 0:
        output = process.stdout.strip()
        return output

    return ""


def eprint(msg):
    print(msg, file=sys.stderr, flush=True)


def fail_and_exit(msg):
    print(msg, file=sys.stderr, flush=True)
    config_manager.restore_hostname()
    sys.exit(1)


def restore_config_file(restore_files):
    for backup, original in restore_files.items():
        if os.path.exists(backup):
            config_manager.restore_config_file(backup, original)


def format_ou_dn(ouaddress, domain):
    if ouaddress:
        fulldn = ",DC=" + domain.replace(".", ",DC=")
        ou = f"OU={ouaddress}" + fulldn
        return ou
    return None


def handle_realmd_join(comp_name, domain, user, passwd, ouaddress):
    restore_files = {
        "/etc/hosts.old": "/etc/hosts",
        "/etc/sssd/sssd.conf.old": "/etc/sssd/sssd.conf",
    }

    if not os.path.isfile("/etc/krb5.conf"):
        fail_and_exit("krb5.conf not found. Required packages might be missing.")

    try:
        result = domain_joiner_realmd.discover(domain)
        if result:
            print("Domain discovered...")
        else:
            fail_and_exit("Domain not found:" + f" '{domain}'")

    except subprocess.CalledProcessError as e:
        print("Error discovering domain. Exit Code:", e.returncode)
        fail_and_exit("Domain discovery failed.")

    try:
        # print("domain:", domain)
        print("Joining the domain...")

        # If there is a sssd file, take a backup.
        sssd_file = "/etc/sssd/sssd.conf"
        sssd_file_backup = "/etc/sssd/sssd.conf.old"
        config_manager.backup_config_file(sssd_file, sssd_file_backup)

        ouaddress = format_ou_dn(ouaddress, domain)

        process = domain_joiner_realmd.join(domain, user, passwd, ouaddress)
        if process.returncode == 0:
            config_manager.update_hostname_file(comp_name, domain)
            config_manager.update_hosts_file(comp_name, domain)

            """if smb_settings:
                config_manager.update_samba_conf_for_sssd(domain)"""

            config_manager.update_sssd_conf(domain)

            subprocess.call(
                ["pam-auth-update", "--enable", "pardus-pam-config"],
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
            )

            print("This computer has been successfully added to the domain.")
            return
        else:
            eprint("Joining domain failed.")
            print("stdout:", process.stdout, flush=True)
            eprint("stderr:" + process.stderr + "\n")

    except Exception as e:
        eprint("Error" + f":{e}")

    # Couldn't connect, restore settings
    restore_config_file(restore_files)
    fail_and_exit("Joining domain failed.")


def handle_winbind_join(comp_name, domain, user, passwd, ouaddress):
    restore_files = {
        "/etc/krb5.conf.old": "/etc/krb5.conf",
        "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
        "/etc/nsswitch.conf.old": "/etc/nsswitch.conf",
        "/etc/hosts.old": "/etc/hosts",
        "/etc/hostname.old": "/etc/hostname",
    }

    found_domain = discover_domain(domain)
    if not found_domain:
        fail_and_exit("Domain not found:" + f" '{domain}'")

    if not os.path.isfile("/etc/krb5.conf"):
        fail_and_exit("krb5.conf not found. Required packages might be missing.")

    try:
        print("Updating /etc/krb5.conf file...")
        update_krb5_config.update_krb5_conf(domain)
        print("Updated /etc/krb5.conf file...")
        config_manager.update_samba_conf_for_winbind(domain)

        p_discover = domain_joiner_winbind.discover()
        if p_discover.returncode != 0:
            print("stdout:", p_discover.stdout, flush=True)
            eprint("stderr:" + p_discover.stderr)
            restore_config_file(restore_files)
            fail_and_exit("Couldn't discovered the domain")

        config_manager.update_nsswitch_conf()
        config_manager.update_hostname_file(comp_name, domain)
        config_manager.update_hosts_file(comp_name, domain)

        process = domain_joiner_winbind.join(user, passwd, ouaddress)
        print("winbind process code:", process.returncode, flush=True)
        print("winbind process stdout:", process.stdout, flush=True)
        print("winbind process stderr:", process.stderr, flush=True)

        if process.returncode == 0 and "Joined" in process.stdout:
            subprocess.run(
                [
                    "systemctl",
                    "restart",
                    "smbd.service",
                    "nmbd.service",
                    "winbind.service",
                ],
                capture_output=True,
            )

            p = domain_joiner_winbind.domain_info()
            print("domain_info process code:", p.returncode, flush=True)
            print("domain_info process stdout:", p.stdout, flush=True)
            print("domain_info process stderr:", p.stderr, flush=True)

            if p.returncode == 0 and p.stdout:
                print("This computer has been successfully added to the domain.")
                return
            else:
                print("stdout:", p.stdout, flush=True)
                eprint("stderr:" + p.stderr)

        # Not joined:
        eprint("Joining domain failed.")
        print("stdout:", process.stdout, flush=True)
        eprint("stderr:" + process.stderr)

    except Exception as e:
        eprint("Error" + f":{e}")

    restore_config_file(restore_files)
    fail_and_exit("")


def join(comp_name, domain, user, passwd, ouaddress=None, realmd=None, winbind=None):
    try:
        # ouaddress = check_ouaddress(ouaddress, domain)
        if realmd:
            config_manager.start_sssd_service()
            subprocess.run(["pam-auth-update", "--enable", "sss"], capture_output=True)

            handle_realmd_join(comp_name, domain, user, passwd, ouaddress)
        elif winbind:
            config_manager.start_winbind_service()
            subprocess.run(["pam-auth-update", "--disable", "sss"], capture_output=True)

            handle_winbind_join(comp_name, domain, user, passwd, ouaddress)
        else:
            print(
                "No domain join method selected. Please specify either realmd or winbind."
            )
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print("An error occurred during the join process:", e.stderr)


def leave(realmd=None, winbind=None, user=None, password=None):
    restore_files = {
        "/etc/hosts.old": "/etc/hosts",
        "/etc/hostname.old": "/etc/hostname",
        "/etc/krb5.conf.old": "/etc/krb5.conf",
        "/etc/nsswitch.conf.old": "/etc/nsswitch.conf",
        "/etc/samba/smb.conf.old": "/etc/samba/smb.conf",
    }

    if not realmd and not winbind:
        eprint("Please provide connection type, realmd or winbind")
        exit(1)

    if realmd:
        p = domain_joiner_realmd.leave(user, password)
    elif winbind:
        p = domain_joiner_winbind.leave(user, password)

    # Success
    print(p.stdout, flush=True)
    eprint(p.stderr)

    if p.returncode == 0:
        return

    # Failure
    restore_config_file(restore_files)
    config_manager.restore_hostname()
    exit(p.returncode)


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
    return ""
