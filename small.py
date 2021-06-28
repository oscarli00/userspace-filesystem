#!/usr/bin/env python

#Created by Oscar Li oli356

from __future__ import print_function, absolute_import, division

import logging
import disktools

from collections import defaultdict
from errno import ENOENT, ENOTEMPTY, ENOTDIR
from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time
from os import getuid, getgid

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

if not hasattr(__builtins__, 'bytes'):
    bytes = str

def get_block_index(path):
    if (len(path)==0 or path == '' or path == '/'):
        return 0

    path = path[1:].split('/')

    current_index = 0

    while len(path) > 0:
        current_block = disktools.read_block(current_index)

        if disktools.bytes_to_int(current_block[63:64]) == 0:
            raise FuseOSError(ENOTDIR)

        file_bitmap = disktools.bytes_to_int(current_block[38:40])
        error = True
        for i in range(0, 16):
            if (1 << i & file_bitmap) != 0:
                block = disktools.read_block(i)
                name_length = disktools.bytes_to_int(block[19:20])
                name = block[20:20+name_length].decode('ascii')
                if name == path[0]:
                    path.pop(0)
                    current_index=i
                    error=False
                    break
        if error:
            raise FuseOSError(ENOENT)

    return current_index

class Memory(LoggingMixIn, Operations):
    'Example memory filesystem. Supports only one level of files.'

    def __init__(self):
        self.fd = 0

    def chmod(self, path, mode):
        block_index=get_block_index(path)
        block=disktools.read_block(block_index)
        mode_bits=disktools.bytes_to_int(block[0:2])
        mode_bits &= 0o770000
        mode_bits |= mode
        block[0:2]=disktools.int_to_bytes(mode_bits, 2)
        disktools.write_block(block_index, block)
        return 0

    def chown(self, path, uid, gid):
        block_index=get_block_index(path)
        block=disktools.read_block(block_index)
        block[2:4]=disktools.int_to_bytes(uid, 2)
        block[4:6]=disktools.int_to_bytes(gid, 2)
        disktools.write_block(block_index, block)

    def create(self, path, mode):
        root_block=disktools.read_block(0)
        free_blocks=disktools.bytes_to_int(root_block[36:38])
        for i in range(0, 16):
            if (1 << i & free_blocks) == 0:
                file_metadata=bytearray(64)
                file_metadata[0:2]=disktools.int_to_bytes(
                    S_IFREG | mode, 2)
                file_metadata[2:4]=disktools.int_to_bytes(
                    getuid(), 2)
                file_metadata[4:6]=disktools.int_to_bytes(
                    getgid(), 2)
                file_metadata[6:7]=disktools.int_to_bytes(
                    1, 1)
                file_metadata[7:11]=disktools.int_to_bytes(
                    int(time()), 4)
                file_metadata[11:15]=disktools.int_to_bytes(
                    int(time()), 4)
                file_metadata[15:19]=disktools.int_to_bytes(
                    int(time()), 4)

                name = path[path.rindex('/')+1:]
                file_metadata[19:20]=disktools.int_to_bytes(len(name), 1)
                file_metadata[20:36]=bytes(name).ljust(16, '\x00'.encode('ascii'))
                file_metadata[40:42]=disktools.int_to_bytes(0, 2)
                parent_index=get_block_index(path[:path.rindex('/')])
                file_metadata[62:63]=disktools.int_to_bytes(parent_index, 1)
                file_metadata[63:64]=disktools.int_to_bytes(0, 1)
                disktools.write_block(i, file_metadata)

                root_block[36:38]=disktools.int_to_bytes(
                    1 << i | free_blocks, 2)
                disktools.write_block(0, root_block)

                parent_block=disktools.read_block(parent_index)
                file_bitmap=disktools.bytes_to_int(parent_block[38:40])
                parent_block[38:40]=disktools.int_to_bytes(
                    1 << i | file_bitmap, 2)
                disktools.write_block(parent_index, parent_block)              

                self.fd += 1
                return self.fd

        raise MemoryError("No free blocks left")

    def getattr(self, path, fh=None):
        block=disktools.read_block(get_block_index(path))
        attrs=dict(
            st_mode=disktools.bytes_to_int(block[0:2]),
            st_uid=disktools.bytes_to_int(block[2:4]),
            st_gid=disktools.bytes_to_int(block[4:6]),
            st_nlink=disktools.bytes_to_int(block[6:7]),
            st_ctime=disktools.bytes_to_int(block[7:11]),
            st_mtime=disktools.bytes_to_int(block[11:15]),
            st_atime=disktools.bytes_to_int(block[15:19]),
            st_size=disktools.bytes_to_int(block[40:42])
        )
        return attrs

    def getxattr(self, path, name, position=0):
        return ''

    def mkdir(self, path, mode):
        root_block=disktools.read_block(0)
        free_blocks=disktools.bytes_to_int(root_block[36:38])
        for i in range(0, 16):
            if (1 << i & free_blocks) == 0:
                file_metadata=bytearray(64)
                file_metadata[0:2]=disktools.int_to_bytes(
                    S_IFDIR | mode, 2)
                file_metadata[2:4]=disktools.int_to_bytes(
                    getuid(), 2)
                file_metadata[4:6]=disktools.int_to_bytes(
                    getgid(), 2)
                file_metadata[6:7]=disktools.int_to_bytes(
                    2, 1)
                file_metadata[7:11]=disktools.int_to_bytes(
                    int(time()), 4)
                file_metadata[11:15]=disktools.int_to_bytes(
                    int(time()), 4)
                file_metadata[15:19]=disktools.int_to_bytes(
                    int(time()), 4)

                name = path[path.rindex('/')+1:]
                file_metadata[19:20]=disktools.int_to_bytes(len(name), 1)
                file_metadata[20:36]=bytes(name).ljust(16, '\x00'.encode('ascii'))
                file_metadata[40:42]=disktools.int_to_bytes(0, 2)
                parent_index=get_block_index(path[:path.rindex('/')])
                file_metadata[62:63]=disktools.int_to_bytes(parent_index, 1)
                file_metadata[63:64]=disktools.int_to_bytes(1, 1)
                disktools.write_block(i, file_metadata)

                root_block[36:38]=disktools.int_to_bytes(
                    1 << i | free_blocks, 2)
                disktools.write_block(0, root_block)

                parent_block=disktools.read_block(parent_index)
                file_bitmap=disktools.bytes_to_int(parent_block[38:40])
                parent_block[38:40]=disktools.int_to_bytes(
                    1 << i | file_bitmap, 2)
                links=disktools.bytes_to_int(parent_block[6:7])+1
                parent_block[6:7] =disktools.int_to_bytes(links,1)
                disktools.write_block(parent_index, parent_block)    
                return          

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        file_metadata=disktools.read_block(get_block_index(path))
        file_size=disktools.bytes_to_int(file_metadata[40:42])
        file_data=bytes()
        remaining=file_size
        block_offset=0
        while remaining > 64:
            block_index=file_metadata[42+block_offset]
            block=disktools.read_block(block_index)
            file_data += bytes(block)
            remaining -= 64
            block_offset += 1

        block=disktools.read_block(file_metadata[42+block_offset])
        file_data += bytes(block[:remaining])
        return file_data[offset:offset + size]

    def readdir(self, path, fh):
        dir_block=disktools.read_block(get_block_index(path))
        file_bitmap=disktools.bytes_to_int(dir_block[38:40])
        result=['.', '..']
        for i in range(0, 16):
            if (1 << i & file_bitmap) != 0:
                block=disktools.read_block(i)
                name_length=disktools.bytes_to_int(block[19:20])
                name=block[20:20+name_length].decode('ascii')
                result += [name]
        return result

    def rename(self, old, new):
        file_metadata=disktools.read_block(get_block_index(old))
        name=new.split('/')[-1]
        file_metadata[19:20]=disktools.int_to_bytes(len(name), 1)
        file_metadata[20:36]=bytearray(name[:], 'ascii')
        disktools.write_block(get_block_index(old), file_metadata)

    def rmdir(self, path):
        index = get_block_index(path)
        block = disktools.read_block(index)

        if disktools.bytes_to_int(block[38:40]) != 0:
            raise FuseOSError(ENOTEMPTY)

        root_block=disktools.read_block(0)
        free_blocks=disktools.bytes_to_int(root_block[36:38])

        # free up metadata block
        root_block[36:38]=disktools.int_to_bytes(
            free_blocks & ~(1 << index), 2)
        disktools.write_block(0, root_block)

        # free up metadata block in parent
        parent_index=disktools.bytes_to_int(block[62:63]) 
        parent_block=disktools.read_block(parent_index)
        file_bitmap=disktools.bytes_to_int(parent_block[38:40])
        parent_block[38:40]=disktools.int_to_bytes(
            file_bitmap & ~(1 << index), 2)
        parent_links = disktools.bytes_to_int(parent_block[6:7])
        parent_block[6:7] = disktools.int_to_bytes(parent_links-1,1)
        disktools.write_block(parent_index, parent_block)


    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def truncate(self, path, length, fh=None):
        root_block=disktools.read_block(0)
        free_blocks=disktools.bytes_to_int(root_block[36:38])
        file_index=get_block_index(path)
        file_metadata=disktools.read_block(file_index)
        file_data=bytes()
        old_size=disktools.bytes_to_int(file_metadata[40:42])
        remaining=disktools.bytes_to_int(file_metadata[40:42])
        block_offset=0
        while remaining > 0:
            block_index=file_metadata[42+block_offset]
            block=disktools.read_block(block_index)
            file_data += bytes(block[:min(64, remaining)])
            remaining -= min(64, remaining)
            block_offset += 1
            free_blocks &= ~(1 << block_index)

        file_data=file_data[:length].ljust(length, '\x00'.encode('ascii'))

        remaining=length
        block_offset=0
        while remaining > 0:
            error=True
            for i in range(0, 16):
                if (1 << i & free_blocks) == 0:
                    file_metadata[42+block_offset]=i
                    disktools.write_block(
                        i, file_data[len(file_data)-remaining:len(file_data)-remaining+min(64, remaining)])
                    remaining -= min(64, remaining)
                    block_offset += 1
                    free_blocks |= 1 << i
                    error=False
                    break
            if error:
                raise MemoryError("No free blocks left")

        file_metadata[40:42]=disktools.int_to_bytes(length, 2)
        disktools.write_block(file_index, file_metadata)
        root_block[36:38]=disktools.int_to_bytes(free_blocks, 2)
        disktools.write_block(0, root_block)

        # update ancestor block size
        parent_index=disktools.bytes_to_int(file_metadata[62:63]) 
        while parent_index != 0:
            parent_block=disktools.read_block(parent_index)
            parent_size=disktools.bytes_to_int(parent_block[40:42])
            parent_size=parent_size - old_size + length
            parent_block[40:42]=disktools.int_to_bytes(parent_size, 2)
            disktools.write_block(parent_index, parent_block)
            parent_index = disktools.bytes_to_int(parent_block[62:63])
        
        parent_block=disktools.read_block(parent_index)
        parent_size=disktools.bytes_to_int(parent_block[40:42])
        parent_size=parent_size - old_size + length
        parent_block[40:42]=disktools.int_to_bytes(parent_size, 2)
        disktools.write_block(parent_index, parent_block)

    def unlink(self, path):
        root_block=disktools.read_block(0)
        free_blocks=disktools.bytes_to_int(root_block[36:38])

        file_index=get_block_index(path)
        block=disktools.read_block(file_index)

        # freeing up data blocks
        size=disktools.bytes_to_int(block[40:42])
        remaining=size
        offset=0
        while remaining > 0:
            free_blocks &= ~(1 << disktools.bytes_to_int(
                block[42+offset:43+offset]))
            remaining -= 64
            offset += 1

        # free up metadata block
        root_block[36:38]=disktools.int_to_bytes(
            free_blocks & ~(1 << file_index), 2)
        disktools.write_block(0, root_block)

        # remove from parent
        parent_index=disktools.bytes_to_int(block[62:63]) 
        parent_block=disktools.read_block(parent_index)
        file_bitmap=disktools.bytes_to_int(parent_block[38:40])
        parent_block[38:40]=disktools.int_to_bytes(
            file_bitmap & ~(1 << file_index), 2)
        parent_size = disktools.bytes_to_int(parent_block[40:42])
        parent_size -= size
        parent_block[40:42] = disktools.int_to_bytes(parent_size,2)
        disktools.write_block(parent_index, parent_block)

    def utimens(self, path, times=None):
        now=time()
        atime, mtime=times if times else (now, now)

        block_index=get_block_index(path)
        block=disktools.read_block(block_index)
        block[15:19]=disktools.int_to_bytes(int(atime), 4)
        block[11:15]=disktools.int_to_bytes(int(mtime), 4)
        disktools.write_block(block_index, block)

    def write(self, path, data, offset, fh):
        root_block=disktools.read_block(0)
        free_blocks=disktools.bytes_to_int(root_block[36:38])

        file_index = get_block_index(path)
        file_metadata=disktools.read_block(file_index)
        file_size=disktools.bytes_to_int(file_metadata[40:42])
        file_data=bytes()
        remaining=file_size
        block_offset=0
        while remaining > 0:
            block_index=disktools.bytes_to_int(
                file_metadata[42+block_offset:43+block_offset])
            block=disktools.read_block(block_index)
            file_data += bytes(block[:min(64, remaining)])
            remaining -= min(64, remaining)
            block_offset += 1
            free_blocks &= ~(1 << block_index)

        file_data=file_data[:offset].ljust(offset, '\x00'.encode(
            'ascii')) + data + file_data[offset + len(data):]

        remaining=len(file_data)
        block_offset=0
        while remaining > 0:
            error=True
            for i in range(0, 16):
                if (1 << i & free_blocks) == 0:
                    file_metadata[42+block_offset:43 +
                                  block_offset]=disktools.int_to_bytes(i, 1)
                    disktools.write_block(
                        i, bytearray(file_data[len(file_data)-remaining:len(file_data)-remaining+min(64, remaining)]))
                    remaining -= min(64, remaining)
                    block_offset += 1
                    free_blocks |= 1 << i
                    error=False
                    break
            if error:
                raise MemoryError("No free blocks left")

        file_metadata[40:42]=disktools.int_to_bytes(len(file_data), 2)
        disktools.write_block(file_index, file_metadata)
        root_block[36:38]=disktools.int_to_bytes(free_blocks, 2)
        disktools.write_block(0, root_block)

        parent_index=disktools.bytes_to_int(file_metadata[62:63]) 
        while parent_index != 0:
            parent_block=disktools.read_block(parent_index)
            parent_size=disktools.bytes_to_int(parent_block[40:42])
            parent_size=parent_size - file_size + len(file_data)
            parent_block[40:42]=disktools.int_to_bytes(parent_size, 2)
            disktools.write_block(parent_index, parent_block)
            parent_index = disktools.bytes_to_int(parent_block[62:63])       
        parent_block=disktools.read_block(parent_index)
        parent_size=disktools.bytes_to_int(parent_block[40:42])
        parent_size=parent_size - file_size + len(file_data)
        parent_block[40:42]=disktools.int_to_bytes(parent_size, 2)
        disktools.write_block(parent_index, parent_block)

        return len(data)

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('mount')
    args=parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    fuse=FUSE(Memory(), args.mount, foreground=True)
