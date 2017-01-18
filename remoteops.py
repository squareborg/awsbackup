import subprocess
import settings

key_file = settings.SSH_KEY_FILE
user = 'ubuntu'

def run_ssh_command(public_ip,command):
    ssh = subprocess.Popen(["ssh","-o","StrictHostKeyChecking=no", "-i", key_file, '{0}@{1}'.format(user,public_ip), command],
                           shell=False,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    res = ssh.communicate()
    if ssh.returncode > 0:
        print("Error below")
        print(res[1])
    return ([ssh.stdout,ssh.stderr])

def run_ssh_command_return_code(public_ip,command):
    print('SSH - public_ip: {0} command: {1}'.format(public_ip,command))
    ssh = subprocess.Popen(["ssh","-o","StrictHostKeyChecking=no", "-i", key_file, '{0}@{1}'.format(user,public_ip), command],
                           shell=False,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    res = ssh.communicate()
    if ssh.returncode > 0:
        print("Error below")
        print(res[1])
    return (ssh.returncode)

def scp(target_ip, source_path, destination_path):
    print('SCP - ip {0} source_path {1} dest_path {2}'.format(target_ip,source_path,destination_path))
    scp = subprocess.Popen(["scp", "-i", key_file, '{0}@{1}:{2}'.format(user, target_ip, source_path), '{0}'.format(destination_path)],
                           shell=False,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    res = scp.communicate()
    if scp.returncode == 0:
        return True
    else:
        print("error below")
        print(res[1])
        return False