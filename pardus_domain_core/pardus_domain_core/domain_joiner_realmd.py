import subprocess

def discover(domain):
    process = subprocess.check_output(["realm", "discover", "-v", domain]).decode("utf-8")
    return process

def join(domain, user, passwd, ouaddress):
    join_command = ["realm", "join", "-v", "-U", user, domain.upper()]

    if ouaddress:
        ou = f"--computer-ou={ouaddress}"
        join_command = ["realm", "join", "-v", "-U", user, ou, domain.upper()]

    print(join_command)
    process = subprocess.run(
        join_command, input=passwd, text=True, capture_output=True
    )
    stderr = process.stderr
    msg = stderr.strip().split("*")[-1]

    return msg

def leave(user, password):
    subprocess.run(["realm", "leave", "-U", user], input=password, text=True, capture_output=True)

def list_realm():
    return subprocess.run(["realm", "list"], capture_output=True)

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
