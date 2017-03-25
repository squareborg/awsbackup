class AwsVolume():

    def __str__(self):
        return self.volume_id

    def __unicode__(self):
        return self.volume_id

    def __init__(self):
        self.volume_id = None
        self.snapshots = []

    def get_latest_snapshot(self):
        return sorted(self.snapshots, key=lambda x: x.start_time,reverse=True)[0]


class AwsSnapshot():

    def __str__(self):
        return self.snapshot_id

    def __unicode__(self):
        return self.snapshot_id

    def __init__(self):
        self.snapshot_id = None
        self.start_time = None
        self.state = None

class AwsInstance():

    def __str__(self):
        return self.instance_id

    def __unicode__(self):
        return self.instance_id

    def __init__(self):
        self.instance_id = None
        self.ip = None
        self.volumes = []
