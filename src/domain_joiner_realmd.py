import subprocess


def discover(domain):
    process = subprocess.run(
        ["realm", "discover", "-v", domain], capture_output=True, text=True
    )

    if process.returncode == 0:
        return process.stdout

    return ""


def join(domain, user, passwd, ouaddress):
    join_command = ["realm", "join", "-v", "-U", user, domain.upper()]

    if ouaddress:
        join_command = [
            "realm",
            "join",
            "-v",
            "-U",
            user,
            "--computer-ou",
            ouaddress,
            domain.upper(),
        ]

    # print(join_command)
    process = subprocess.run(join_command, input=passwd, text=True)

    return process


def leave(user, password):
    return subprocess.run(["realm", "leave", "-U", user], input=password, text=True)


def list_realm():
    return subprocess.run(["realm", "list"], capture_output=True)


def permit(user=None, domain=None, all=None):
    if all:
        subprocess.run(["realm", "permit", "-all"], check=True)
    else:
        if not user or not domain:
            raise ValueError(
                "User and domain must be specified or 'all=True' must be used."
            )
        permit_user = f"{user}@{domain}"
        subprocess.run(["realm", "permit", permit_user], check=True)


def deny():
    subprocess.run(["realm", "deny", "-a"], check=True)
