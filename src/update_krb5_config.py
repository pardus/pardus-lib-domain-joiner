import os
import shutil


def backup_config_file(src, dst):
    if os.path.exists(src):
        shutil.copy2(src, dst)

def read_krb5_conf(path):
    with open(path, "r") as f:
        return f.readlines()

def write_krb5_conf(path, lines):
    with open(path, "w") as f:
        f.writelines(lines)


def update_libdefaults(lines, default_realm):
    updated = False
    result = []
    in_section = False

    for line in lines:
        if line.strip().startswith("[libdefaults]"):
            in_section = True
            result.append(line)
            continue
        elif line.strip().startswith("[") and in_section:
            in_section = False

        if in_section and line.strip().startswith("default_realm"):
            result.append(f"        default_realm = {default_realm}\n")
            updated = True
        else:
            result.append(line)

    if not updated:
        result.append("\n[libdefaults]\n")
        result.append(f"        default_realm = {default_realm}\n")

    return result


def extract_existing_entries(lines, section_name):
    entries = set()
    in_section = False

    for line in lines:
        if line.strip() == f"[{section_name}]":
            in_section = True
            continue
        elif line.strip().startswith("[") and in_section:
            break
        elif in_section:
            if "=" in line:
                key = line.split("=")[0].strip()
                entries.add(key)

    return entries


def insert_into_section(lines, section_name, block):
    new_lines = []
    inserted = False

    for line in lines:
        new_lines.append(line)
        if line.strip() == f"[{section_name}]" and not inserted:
            new_lines.append(block)
            inserted = True

    if not inserted:
        new_lines.append(f"\n[{section_name}]\n")
        new_lines.append(block)

    return new_lines


def update_krb5_conf(domain):
    domain_upper = domain.upper()
    krb5_file = "/etc/krb5.conf"
    krb5_file_backup = "/etc/krb5.conf.old"

    backup_config_file(krb5_file, krb5_file_backup)
    if os.path.exists(krb5_file):
        lines = read_krb5_conf(krb5_file)

        # setting blocks
        default_realm = domain_upper
        realms_block = f"\t{domain_upper} = {{\n\t\tkdc = {domain}:88\n\t\tadmin_server = {domain}:749\n\t}}\n"
        domain_realm_block = (
            f"\t.{domain} = {domain_upper}\n\t{domain} = {domain_upper}\n"
        )

        # update libdefaults
        lines = update_libdefaults(lines, default_realm)

        # existents
        known_realms = extract_existing_entries(lines, "realms")
        known_domains = extract_existing_entries(lines, "domain_realm")

        # just add new ones
        if domain_upper not in known_realms:
            lines = insert_into_section(lines, "realms", realms_block)
        if domain not in known_domains and f".{domain}" not in known_domains:
            lines = insert_into_section(lines, "domain_realm", domain_realm_block)
        
        write_krb5_conf(krb5_file, lines)
