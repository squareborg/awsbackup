Backup AWS instance volumes to local tar.gz
==========================================

***WARNING***

Developement software, not fit for purpose.

***END OF WARNING***

This is the very alpha start of a bigger project. This at the moment will conect to AWS, query all instances tagged with key:value  backup:1, then check to see if its due to backup that instance. If it is, it creates a temporary instance, with the latest snapshot of your target instance as a secondary mounted volume. It then tar.gz that volume and then downloads it locally for keeping offsite.


