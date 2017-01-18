from __future__ import with_statement
import boto3
from datetime import datetime, timedelta

from myaws import AwsInstance, AwsVolume, AwsSnapshot
from archive import Archive, Archiver, ArchiveStorage
import settings


frequency = timedelta(settings.FREQUENCY)

archive_storage = ArchiveStorage()
archive_storage.path = settings.STORAGE_PATH
archive_storage.initialise()

ec2 = boto3.resource('ec2',region_name=settings.REGION)

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
        archiver = Archiver()
        archiver.target_instance = instance
        archiver.create()
        if archiver.run_archive():
            print('Successfully backed up {0}'.format(instance.instance_id))
        else:
            print('eek something went wrong with archiving {0}'.format(instance.instance_id))
        archiver.destroy()