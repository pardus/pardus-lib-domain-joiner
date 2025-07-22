import subprocess

def discover(domain):
    # [samba-tool domain info domain_name]
    process = subprocess.check_output(["realm", "discover", "-v", domain]).decode("utf-8")
    return process

def join():
    # [samba-tool domain join domain_name DC -U Administrator]
    pass

def leave():
    #  samba-tool domain demote --remote-other-dead-server=AD -UAdministrator
    pass

def info():
    # [samba-tool user list]    
    pass