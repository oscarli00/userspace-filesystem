# FUSE (Filesystem in Userspace)
A small userspace filesytem created for SOFTENG370: Operating Systems. The filesystem created contains 16 blocks of 64 bytes each and supports commands such as ```touch, echo, cat, ls, rm, mkdir, rmdir```.

## How to use:
1. Create a directory named "mount" (```mkdir mount```)
2. Run disktools.py to create a file called my-disk (```python disktools.py```)
3. Run format.py to format my-disk (```python format.py```)
4. Start the file system using small.py (```python small.py mount```)

Run ```od --address-radix=x -t x1 -a my-disk``` to show the bytes of ```my-disk```.
