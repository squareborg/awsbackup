from __future__ import with_statement
import boto3
from datetime import datetime, timedelta

from myaws import AwsInstance, AwsVolume, AwsSnapshot
from archive import Archive, Archiver, ArchiveStorage
import settings
import os

# Do some checks

if os.path.isdir(settings.STORAGE_PATH):
    try:
        testfilepath = os.path.join(settings.STORAGE_PATH, '.awsbackuptestfile')
        with open(testfilepath,'w') as testfile:
            testfile.write("testing")
    except PermissionError as err:
        print('Critical not sufficent privileges to write into storage location {0}'.format(err))
        exit()
    else:
        os.unlink(testfilepath)
else:
    print('Critical: Cannot find storage path {0}'.format(settings.STORAGE_PATH))
    exit()


key_file = settings.SSH_KEY_FILE
if os.path.isfile(key_file):
    key_file_statinfo = os.stat(key_file)
    if oct(key_file_statinfo.st_mode & 0o0777) == '0o600':
        # todo check if key is a valid key, then check it works
        pass
    else:
        print('Critical: ssh key {0} does not have correct permissions Require mode 600'.format(key_file))
        exit()
else:
    print('Critical: Cannot find ssh key {0}'.format(key_file))
    exit()

if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
    print('Critical: Cannot find credentials, is AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY not set?')
    exit()

frequency = timedelta(settings.FREQUENCY)

archive_storage = ArchiveStorage()
archive_storage.path = settings.STORAGE_PATH
archive_storage.initialise()

ec2 = boto3.resource('ec2',region_name=settings.REGION)

# Delete any old archivers

filters = [{'Name':'tag:hypersrvbackuparchiver', 'Values':['True']}]
archiver_instances = ec2.instances.filter(Filters=filters)
for archiver_instance in archiver_instances:
    print('Found old archiver {0}, terminating...'.format(archiver_instance.id))
    archiver_instance.terminate()

my_instances = []
filters = [{'Name':'tag:backup', 'Values':['1']}]
ec2instances = ec2.instances.filter(Filters=filters)
for i in ec2instances:
    my_instance = AwsInstance()
    my_instance.instance_id = i.id
    for volume in i.volumes.all():
        this_volume = AwsVolume()
        this_volume.volume_id = volume.id
        v_snaps = volume.snapshots.all()
        for v_snap in [ s for s in v_snaps if s.state == 'completed']:
            my_v_snap= AwsSnapshot()
            my_v_snap.snapshot_id = v_snap.id
            my_v_snap.start_time = v_snap.start_time.replace(tzinfo=None)
            my_v_snap.state = v_snap.state
            this_volume.snapshots.append(my_v_snap)
        my_instance.volumes.append(this_volume)
    my_instances.append(my_instance)

for instance in my_instances:
    last_backup = archive_storage.get_last_backup_by_instance_id(instance.instance_id)
    if last_backup:
        delta = datetime.now()-last_backup.snapshot_start_time
        if delta > frequency:
            run = True
            # Lets check that there is a newer archive on aws
            aws_latest = instance.volumes[0].get_latest_snapshot()
            storage_latest = archive_storage.get_last_backup_by_instance_id(instance.instance_id)
            print('aws_latest: {0} '.format(aws_latest.start_time))
            print('storage_latest: {0} '.format(storage_latest.snapshot_start_time))
            if aws_latest.start_time > storage_latest.snapshot_start_time:
                print("Aws has later snapshot")
            else:
                run = False
                print("Aws does not have a later snapshot")
        else:
            print('Instance {0} is not due for archiving'.format(instance.instance_id))
            run = False

    else:
        run = True
    if (run):
        print('Instance {0} is due for archiving'.format(instance.instance_id))
        if len(instance.volumes[0].snapshots) > 0:
            archiver = Archiver()
            archiver.target_instance = instance
            archiver.create()
            if archiver.run_archive():
                print('Successfully backed up {0}'.format(instance.instance_id))
            else:
                print('eek something went wrong with archiving {0}'.format(instance.instance_id))
            archiver.destroy()
        else:
            print('No snapshots available, skipping')