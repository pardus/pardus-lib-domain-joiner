import subprocess


def get_returncode(process):
    if process.returncode == 0:
        return True
    return False

def discover():
    return subprocess.run(["net", "ads", "info"], capture_output=True, text=True)

def join(user, password, ouaddress):
    join_command = ["net", "ads", "join", "-v", "-U", user]

    if ouaddress:
        ou = f'createcomputer="{ouaddress}"'
        join_command = ["net", "ads", "join", "-v", "-U", user, ou]
    return subprocess.run(join_command, input=password, text=True, capture_output=True)

def leave(user, password):
    return subprocess.run(["net", "ads", "leave", "-U", user], input=password, text=True)

def domain_info():
    return subprocess.run(["net", "ads", "testjoin"], capture_output=True)

def list_users():
    # subprocess.run(["net", "ads", "user"])
    return subprocess.run(["wbinfo", "-u"], capture_output=True)

def list_group():
    return subprocess.run(["wbinfo", "-g"], capture_output=True)