#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import time
import stat
import io
import ctypes
import struct
import zlib

# https://users.cs.jmu.edu/buchhofp/forensics/formats/pkzip.html
# https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT
# https://en.wikipedia.org/wiki/Zip_(file_format)#File_headers

ZIP_VERSION = b'\x14'  # copied from output of the zipfile Python module
BLOCKSIZE = io.DEFAULT_BUFFER_SIZE # usually 8192
USE_DATA_DESCRIPTOR = True   # required to be true for compliance to the spec

LOCAL_FILE_HEADER_SIZE = 30 # local file header + data descriptor (local file footer)
if USE_DATA_DESCRIPTOR:
    LOCAL_FILE_HEADER_SIZE += 16
CENTRAL_DIRECTORY_FILE_HEADER_SIZE = 46
CENTRAL_DIRECTORY_FOOTER_SIZE = 22

FLAGS = (1 << 3 | 1 << 11) # flags: hide checksum (bit 3), UTF-8 names (bit 11)

# See: https://unix.stackexchange.com/a/14727/234161
# To quote, this is the layout used on Unix:
#     TTTTsstrwxrwxrwx0000000000ADVSHR
#     ^^^^____________________________ file type as explained above
#         ^^^_________________________ setuid, setgid, sticky
#            ^^^^^^^^^________________ permissions
#                     ^^^^^^^^________ This is the "lower-middle byte" your post mentions
#                             ^^^^^^^^ DOS attribute bits
EXTERNAL_ATTRIBUTES = (stat.S_IFREG | 0o664) << 16 # use a sane default

class ZipFileChanged(Exception):
    '''
    Raised when the stat() filesize isn't the same as the read filesize.
    '''
    pass

class ZipFile:
    def __init__(self, path, zipname, st, offset):
        self.path = path
        self.zipname = zipname
        self.st = st
        self.localHeaderOffset = offset

    def localSize(self):
        '''
        Calculate the size of the local header + data.
        Every file will take up this space plus the space in the central directory.
        '''
        return LOCAL_FILE_HEADER_SIZE + len(self.zipname) + self.st.st_size

    def centralDirectorySize(self):
        '''
        Return the size of the file entry in the central directory.
        '''
        return CENTRAL_DIRECTORY_FILE_HEADER_SIZE + len(self.zipname)

    def totalSize(self):
        '''
        Return all space this file takes in the zipfile.
        '''
        return self.localSize() + self.centralDirectorySize()

    def dos_time(self):
        '''
        Convert a timestamp to the weird DOS format the ZIP format uses - which
        uses a simple naive date/time encoding function instead of storing the
        GMT time in seconds like so many other formats do.
        '''
        ts = time.localtime(self.st.st_mtime)
        return (ts.tm_sec // 2) | (ts.tm_min << 5) | (ts.tm_hour << 11)

    def dos_date(self):
        '''
        See dos_time
        '''
        ts = time.localtime(self.st.st_mtime)
        return (ts.tm_mday) | (ts.tm_mon << 5) | ((ts.tm_year - 1980) << 9)

class ZipSeeker:
    def __init__(self):
        self.files = []

    def add(self, path, zipname=None):
        '''
        Add a file to this ZIP.
        Doesn't actually read the file, only stat()s it.
        You may need to provide another name for use within the ZIP.
        '''
        if zipname is None:
            zipname = path
        st = os.stat(path)
        offset = 0
        if len(self.files):
            offset = self.files[-1].localHeaderOffset + self.files[-1].localSize()
        self.files.append(ZipFile(path, zipname.encode('utf-8'), st, offset))

    def size(self):
        '''
        Calculate and return the zip file size before generating it.
        '''
        size = sum(map(lambda f: f.totalSize(), self.files))
        size += CENTRAL_DIRECTORY_FOOTER_SIZE
        return size

    def lastModified(self):
        '''
        Return the last last-modified time of all files in this ZIP file.
        '''
        return max(map(lambda f: f.st.st_mtime, self.files))

    def centralDirectorySize(self):
        '''
        Internal helper function.
        Calculate the length of the central directory (all entries in the
        central directory, excluding the end-of-central-directory entry).
        '''
        size = 0
        for file in self.files:
            size += CENTRAL_DIRECTORY_FILE_HEADER_SIZE + len(file.zipname) # central directory header
        return size

    def centralDirectoryStart(self):
        '''
        Internal helper function.
        Calculate the start index of the central directory.
        '''
        size = 0
        for file in self.files:
            size += file.st.st_size                            # (uncompressed) file itself
            size += LOCAL_FILE_HEADER_SIZE + len(file.zipname) # central directory header
        return size

    def blocks(self):
        for file in self.files:

            # local file header
            # length is 30 bytes (LOCAL_FILE_HEADER_SIZE)
            yield struct.pack('<IccHHHHIIIHH',
                0x04034b50,             # 4-byte signature ("PK\x03\x04")
                ZIP_VERSION, b'\x00',   # 2-byte PKZIP version
                FLAGS,                  # 2-byte flags
                0,                      # 2-byte compression (no compression)
                file.dos_time(),        # 2-byte modtime in MS-DOS format
                file.dos_date(),        # 2-byte moddate in MS-DOS format
                0,                      # 4-byte checksum - stored in data descriptor
                file.st.st_size,        # 4-byte compressed size
                file.st.st_size,        # 4-byte uncompressed size
                len(file.zipname),      # 2-byte filename length
                0)                      # 2-byte extra field length

            # Write the zip filename
            yield file.zipname

            # actual file data (without compression)
            checksum = 0
            size = 0
            fp = open(file.path, 'rb')
            buf = fp.read(BLOCKSIZE)
            while buf:
                size += len(buf)
                if size > file.st.st_size:
                    raise ZipFileChanged('file %s at least %d bytes too big' % (repr(file.zipname), size - file.st.st_size))
                checksum = zlib.crc32(buf, checksum) & 0xffffffff
                yield buf
                buf = fp.read(BLOCKSIZE)
            fp.close()
            if size != file.st.st_size:
                raise ZipFileChanged('file %s with size %d doesn\'t match st_size %d' % (repr(file.zipname), size, file.st.st_size))
            file.checksum = checksum

            # Data descriptor
            # Not strictly necessary, but doesn't add much overhead and might
            # help ZIP readers. It is strictly required by the standard (MUST)
            # but ZIP readers seem to work fine without it.
            # length is 16 bytes (see LOCAL_FILE_HEADER_SIZE)
            if USE_DATA_DESCRIPTOR:
                yield struct.pack('<IIII',
                    0x08074b50, # 4-byte signature: "PK\x07\x08"
                    checksum,   # 4-byte checksum
                    size,       # 4-byte compressed size
                    size)       # 4-byte uncompressed size


        # Write the central directory file headers
        # Length is 46 bytes + file name (CENTRAL_DIRECTORY_FILE_HEADER_SIZE)
        for file in self.files:
            yield struct.pack('<IccccHHHHIIIHHHHHII',
                0x02014b50,                 # 4-byte signature: "PK\x01\x02"
                ZIP_VERSION, b'\x03',       # 2-byte system and version, copied from Python zipfile output
                ZIP_VERSION, b'\x00',       # 2-byte PKZIP version needed
                FLAGS,                      # 2-byte flags
                0,                          # 2-byte compression (no compression)
                file.dos_time(),            # 2-byte last modified time (local time)
                file.dos_date(),            # 2-byte last modified date (local time)
                file.checksum,              # 4-byte CRC-32 checksum
                file.st.st_size,            # 4-byte compressed size (not read due to flag bit 3 being set)
                file.st.st_size,            # 4-byte uncompressed size (not read due to flag bit 3 being set)
                len(file.zipname),          # 2-byte filename length
                0,                          # 2-byte extra field length
                0,                          # 2-byte comment length (no comment)
                0,                          # 2-byte disk number (no split archives, always 0)
                0,                          # 2-byte internal attributes, TODO detect text files
                EXTERNAL_ATTRIBUTES,        # 4-byte external attributes
                file.localHeaderOffset)     # 4-byte offset (index) of local header

            # file name
            yield file.zipname

        # Write the end of central directory record

        # length is 22 bytes (CENTRAL_DIRECTORY_FOOTER_SIZE)
        yield struct.pack('<IHHHHIIH',
            0x06054b50,                     # 4-byte signature: "PK\x05\x06"
            0,                              # 2-byte disk number - always 0 (we don't split)
            0,                              # 2-byte disk with central directory - always 0 (we don't split)
            len(self.files),                # 2-byte number of central directory entries on this disk
            len(self.files),                # 2-byte total number of central directory entries
            self.centralDirectorySize(),    # 4-byte index of start of central directory
            self.centralDirectoryStart(),   # 4-byte size of central directory (without this footer)
            0)                              # 2-byte comment length - we don't use comments

    def blocksOffset(self, start=0, end=None):
        # TODO: optimize start=0 and end=None

        pos = 0
        for block in self.blocks():
            if pos+len(block) <= start:
                # stream hasn't started
                pos += len(block)
                continue
            if end is not None and pos >= end:
                # EOF
                break

            # start index in the block
            if pos >= start:
                startblock = 0
            else:
                startblock = start - pos

            # end index of the block
            if end is None or pos+len(block) <= end:
                endblock = len(block)
            else:
                endblock = end - pos

            if startblock == 0 and endblock == len(block):
                yield block
            else:
                yield block[startblock:endblock]

            pos += len(block)


    def writeStream(self, out, start=0, end=None):
        for block in self.blocksOffset(start, end):
            out.write(block)
