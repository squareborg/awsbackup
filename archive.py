import boto3
import os
import re
import settings
from datetime import datetime
from remoteops import run_ssh_command_return_code, scp


class Archive():

    def __str__(self):
        return 'Archive of {0} on {1}'.format(self.instance_id, self.snapshot_start_time)

    def __unicode__(self):
        return 'Archive of {0} on {1}'.format(self.instance_id, self.snapshot_start_time)

    def __init__(self):
        self.instance_id = None
        self.file_name = None
        self.snapshot_id = None
        self.snapshot_start_time = None

    def get_name(self):
        if self.instance_id and self.snapshot_id:
            return '{0}_{1}_{2}.tar.gz'.format(self.instance_id,self.snapshot_id,self.snapshot_start_time.strftime('%d-%m-%Y_%H-%M-%S'))

    def is_valid_name(self):
        regex = r"(i-(?:[a-z0-9]{8}|[a-z0-9]{17}|))_(snap-(?:[a-z0-9]{8}|[a-z0-9]{17}|))_([0-9]{2}-[0-9]{2}-[0-9]{4}_[0-9]{2}-[0-9]{2}-[0-9]{2})\.tar\.gz$"
        return re.search(regex, self.file_name)




class ArchiveStorage():

    def __init__(self):
        self.path = None
        self.backups = []

    def initialise(self):
        self.get_all_backups()

    def get_archive_from_file_name(self,file_name):
        ret_arc = Archive()
        ret_arc.file_name = file_name
        if ret_arc.is_valid_name():
            regex = r"(i-(?:[a-z0-9]{8}|[a-z0-9]{17}|))_(snap-(?:[a-z0-9]{8}|[a-z0-9]{17}|))_([0-9]{2}-[0-9]{2}-[0-9]{4}_[0-9]{2}-[0-9]{2}-[0-9]{2})\.tar\.gz$"
            match = re.search(regex, file_name)
            ret_arc.file_name = file_name
            ret_arc.instance_id = match.groups()[0]
            ret_arc.snapshot_id = match.groups()[1]
            start_date = datetime.strptime(match.groups()[2], '%d-%m-%Y_%H-%M-%S')
            ret_arc.snapshot_start_time = start_date
            return ret_arc
        else:
            raise ValueError('Not a valid file name')

    def get_all_backups(self):
        if not self.path:
            raise ValueError('No storage path set')
        archives = [f for f in os.listdir(self.path) if os.path.isfile(os.path.join(self.path, f))]
        for arc in archives:
            try:
                this_arc = self.get_archive_from_file_name(arc)
            except Exception:
                print('Error: Not a valid file {0}'.format(arc))
            else:
                self.backups.append(this_arc)

    def get_backups_by_instance_id(self,instance_id):
        return [b for b in self.backups if b.instance_id == instance_id]

    def get_last_backup_by_instance_id(self,instance_id):
        instance_backups = self.get_backups_by_instance_id(instance_id)
        if len(instance_backups) > 0:
            return sorted(instance_backups, key=lambda x: x.snapshot_start_time,reverse=True)[0]
        else:
            return None


class Archiver():

    def __init__(self):
        self.instance_id = None
        self.target_snapshot = None
        self.target_instance = None
        self.ip = None

    def create(self):
        if self.target_instance:
            self.target_snapshot = self.target_instance.volumes[0].get_latest_snapshot()
            print('AWS: Latest snapshot {0}: '.format(self.target_snapshot.snapshot_id))
            BlockDeviceMapping = [
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'SnapshotId': 'snap-04996ed4fc6de4761' # Ubuntu
                    }
                },
                {
                    'DeviceName': '/dev/sdb',
                    'Ebs': {
                        'SnapshotId': self.target_snapshot.snapshot_id
                    }
                }
            ]
            ec2 = boto3.resource('ec2', region_name=settings.REGION)
            res = ec2.create_instances(
                DryRun=False,
                ImageId=settings.ARCHIVER_AMI,
                KeyName=settings.AWS_SSH_KEY,
                InstanceType='t2.nano',
                SecurityGroups=[settings.SECURITY_GROUP], MinCount=1, MaxCount=1,
                BlockDeviceMappings=BlockDeviceMapping
            )
            if res[0].id:
                self.instance_id = res[0].id
                print('Created Archiver: {0}, waiting for instance checks ok'.format(res[0].id))
                ec2c = boto3.client('ec2', region_name=settings.REGION)
                instance_running = ec2c.get_waiter('instance_status_ok')
                instance_running.wait(InstanceIds=[res[0].id])
                print('Started: {0}'.format(res[0].id))
                # get its ip
                for i in ec2.instances.filter(InstanceIds=[res[0].id]):
                    self.ip = i.public_ip_address
        else:
            print("No target instance set")
            return False

    def destroy(self):
        ec2 = boto3.resource('ec2', region_name='eu-west-1')
        ec2.instances.filter(InstanceIds=[self.instance_id]).terminate()

    def volume_mounted(self):
        if run_ssh_command_return_code(self.ip,'mount | grep xvdb1') == 0:
            return True
        else:
            return False


    def mount_volume(self):
        command = 'sudo mount /dev/xvdb1 /mnt'
        if (run_ssh_command_return_code(self.ip,command)) == 0:
            print("mount command success")
            return True
        else:
            print("mount command failure")
            return False

    def create_volume_archive(self):
        print('Creating tar ball of Volume {0} for: {1}'.format(self.target_instance.volumes[0].volume_id,self.target_instance.instance_id))
        if not self.volume_mounted():
            print("Volume not mounted, mounting...")
            self.mount_volume()
        else:
            print("volume already mounted:")
        print("Starting tar archive")
        command = "sudo tar cvzf /home/ubuntu/sdb.tar.gz /opt"
        if run_ssh_command_return_code(self.ip,command) == 0:
            return True
        else:
            return False

    def copy_archive_local(self):
        print('Copying archive local for: {0} '.format(self.target_instance.instance_id))
        this_archive_storage = ArchiveStorage()
        this_archive_storage.path = settings.STORAGE_PATH
        this_archive = Archive()
        this_archive.instance_id = self.target_instance
        this_archive.snapshot_id = self.target_snapshot
        this_archive.snapshot_start_time = self.target_snapshot.start_time
        return scp(self.ip,'/home/ubuntu/sdb.tar.gz',os.path.join(this_archive_storage.path,this_archive.get_name()))


    def run_archive(self):
        if self.create_volume_archive():
            return self.copy_archive_local()
        else:
            return False


