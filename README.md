Backup AWS instance volumes to local tar.gz for offsite backup
==============================================================

***WARNING***

Developement software, not fit for purpose. Use at own risk

***END OF WARNING***

# What it does right now

You set a frequency of backups in `settings.py` value is in days at the moment eg. `FREQUENCY = 7 `

1. Finds all instances tagged with key:value  `backup:1`
2. Checks if the target instance is due a backup, by checking when the last backup was done and seeing if its greater than settings.FREQUENCY
3. Create a temporary instance (Archiver) to perform archiving task
4. Mounts the latest snapshot of the target instance into the Archive at /mnt
5. runs tar cvzf /home/ubuntu/sdb.tar.gz /mnt
6. SCP's the tar.gz back to local machine and stores it
7. Terminates the temporary Archiver instance
8. Moves on to next instance




