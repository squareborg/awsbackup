Backup AWS instance volumes to local tar.gz for offsite backup
==============================================================

***WARNING***

Developement software, not fit for purpose. Use at own risk

***END OF WARNING***

# What it does right now

You set a frequency of backups in `settings.py` value is in days at the moment eg. `FREQUENCY = 7 `

1. Finds all instances tagged with key:value  `backup:1`
2. Checks if the target instance is due a backup, by checking when the last backup was done and seeing if its greater than settings.FREQUENCY
3. Creates a temporary instance (Archiver) to perform archiving task
4. Mounts the latest snapshot of the target instance into the Archiver at /mnt
5. runs tar cvzf /home/ubuntu/sdf.tar.gz /mnt
6. SCP's the tar.gz back to local machine and stores it
7. Terminates the temporary Archiver instance
8. Moves on to next instance, back to step 2


# How to use

`git clone https://github.com/stedotmartin/awsbackup.git`

We require these things

* You need to schedule snaphots of your ec2 instances, to do this you can use CloudWatch, but I like to use [Cloud Ranger](https://cloudranger.com/) As they make it easy to delete off old snapshots
* You need to add tags to your EC2 instances that you want to backup to your local box, the tag should be name: `backup` value: `1`
* Frequency in days you want to backup instances, so to make a local backup every week use `7`
* Storage path, on you local box, path to where you want to store your backed up instances
* SSH keyfile created in EC2 region, need the name it is called in AWS as well as the path to it on your local box
* AWS IAM user with `AmazonEC2FullAccess` permission, Access Key, Secret
* AWS Region ( only one region per run ) need to fix this
* AMI image id for temporary archive instance, Must be `Ubuntu` at the moment. Eg. in Oregon (us-west-2) `ami-b7a114d7`, you also need the images root volume snapshot so for `ami-b7a114d7` this is `snap-b7ae1993`
* EC2 Security group in your regions default VPC, this security group should allow ssh in from your local box where you are storing backups

Once you have all these you can edit 'settings.py'

An example:

	STORAGE_PATH = '/home/ubuntu/backups/' # path on local box
	FREQUENCY = 7 # new backup every week
	REGION = 'us-west-2'
	SSH_KEY_FILE = '/home/ubuntu/.ssh/aws2.pem'
	AWS_SSH_KEY = 'aws2'
	ARCHIVER_AMI = 'ami-b7a114d7' # Ubuntu in Oregon
	ARCHIVER_AMI_SNAPSHOT = 'snap-b7ae1993' # Ubuntu in Oregon
	SECURITY_GROUP = 'backup'


## How to run

Right now I am using like this.

Create a script, my example is `backup_oregon.sh` with the following inside ( update the path to suit your setup )

    AWS_ACCESS_KEY_ID=YOURACCESSKEYID AWS_SECRET_ACCESS_KEY=YOURSECRET python3 /home/ubuntu/awsbackup/awsbackupcli.py

To run one time just run your script. 

Now setup a cronjob like this again updating the paths to what you have

	crontab -e

	# m h  dom mon dow   command
	0 */12 * * * ps aux | grep "python3 /home/ubuntu/awsbackup/awsbackupcli.py" | grep -v grep ||  /home/ubuntu/awsbackup/backup_oregon.sh

Now it will keep checking to see if it needs to pull down an image
