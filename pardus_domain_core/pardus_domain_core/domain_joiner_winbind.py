import subprocess


def get_returncode(process):
    if process.returncode == 0:
        return True
    return False

def discover():
    process = subprocess.run(["net", "ads", "info"])
    get_returncode(process)

def join(user, password, ouaddress):
    """ouaddress.split("cn")[-1]
    ou = f"'-ou={ouaddress}'" """
    return subprocess.run(["net", "ads", "join", "-v", "-U", user], input=password, text=True, capture_output=True)

def leave(user, password):
    return subprocess.run(["net", "ads", "leave", "-U", user], input=password, text=True, capture_output=True)

def domain_info():
    process = subprocess.run(["net", "ads", "testjoin"])
    return get_returncode(process)

def list_users():
    # subprocess.run(["net", "ads", "user"])
    return subprocess.run(["wbinfo", "-u"], capture_output=True)

def list_group():
    return subprocess.run(["wbinfo", "-g"], capture_output=True)