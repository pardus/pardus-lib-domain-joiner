import subprocess

def discover(domain):
    process = subprocess.check_output(["realm", "discover", "-v", domain]).decode("utf-8")
    return process

def join(domain, user, passwd, ouaddress):
    ou = f"--computer-ou={ouaddress}"
    join_command = [
        "realm", "join", "-v", "-U", user, ou, domain.upper()
    ]
    """join_command = ['realm join -v --computer-ou="' + ouaddress + '" --user="' + user + "@" + domain.upper() + '" ' + domain.lower()]"""
    print(join_command)
    process = subprocess.run(
        join_command, input=passwd, text=True, capture_output=True
    )
    stderr = process.stderr
    msg = stderr.strip().split("*")[-1]

    return msg

def leave():
    subprocess.run(["realm", "leave", "-v"], check=True)

def list_realm():
    return subprocess.run(["realm", "list"])

def permit(user=None,domain=None,all=None):
    if all:
        subprocess.run(["realm", "permit", "-all"], check=True)
    else:
        if not user or not domain:
            raise ValueError("User and domain must be specified or 'all=True' must be used.")
        permit_user = f"{user}@{domain}"
        subprocess.run(["realm", "permit", permit_user], check=True)

def deny():
    subprocess.run(["realm", "deny", "-a"], check=True)
