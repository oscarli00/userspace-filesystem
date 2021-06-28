#!/usr/bin/env python

#Created by Oscar Li oli356

import disktools

from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time
from os import getuid, getgid

NUM_BLOCKS = 16
BLOCK_SIZE = 64
DISK_NAME = 'my-disk'

#block 0
#stores metadata of root ('/')
now = int(time())
root_metadata = dict(
    name='/',
    mode=(S_IFDIR | 0o755),
    uid=getuid(),
    gid=getgid(),
    ctime=now,
    mtime=now,
    atime=now,
    nlink=2)

root_block = bytearray(BLOCK_SIZE)
root_block[0:2] = disktools.int_to_bytes(root_metadata['mode'], 2)
root_block[2:4] = disktools.int_to_bytes(root_metadata['uid'], 2)
root_block[4:6] = disktools.int_to_bytes(root_metadata['gid'], 2)
root_block[6:7] = disktools.int_to_bytes(root_metadata['nlink'], 1)
root_block[7:11] = disktools.int_to_bytes(root_metadata['ctime'], 4)
root_block[11:15] = disktools.int_to_bytes(root_metadata['mtime'], 4)
root_block[15:19] = disktools.int_to_bytes(root_metadata['atime'], 4)
root_block[19:20] = disktools.int_to_bytes(len(root_metadata['name']), 1)
root_block[20:36] = bytes(root_metadata['name']).ljust(16, '\x00'.encode('ascii'))

#storing which blocks are used as bitmap
root_block[36:38] = disktools.int_to_bytes(1, 2)

#storing which blocks contain child file metadata as bitmap
root_block[38:40] = disktools.int_to_bytes(0, 2)

#bytes 40:42 is for file size
#bytes 42:58 is for location of data blocks

#bytes 62:63 is for parent index

#bytes 63:64 is 0 for file, 1 for directory
root_block[63:64] = disktools.int_to_bytes(1, 1)

disktools.write_block(0,root_block)
