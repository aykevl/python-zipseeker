#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import io
import unittest
import random

PY2 = sys.version_info[0] <= 2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from zipseeker import ZipSeeker

class Test(unittest.TestCase):

    def test_all(self):

        outfile = '/tmp/zipseeker-test.zip'

        fp = ZipSeeker()
        fp.add('testfiles/test.txt', 'test.txt')
        if PY2:
            fp.add('testfiles/test-µ.txt', u'test-µ.txt')
        else: # PY3
            fp.add('testfiles/test-µ.txt', 'test-µ.txt')

        # calculate the size beforehand
        size = fp.size()

        out = open(outfile, 'wb')
        for block in fp.blocks():
            out.write(block)
        out.close()

        st = os.stat(outfile)
        if st.st_size != size:
            raise RuntimeError('expected zip file size to be %d, but it is %d' % (size, st.st_size))

        zipdata = open(outfile, 'rb').read()

        for i in range(0, len(zipdata)):
            # all start positions with a fixed end position
            f = io.BytesIO()
            fp.writeStream(f, i, None)
            if f.getvalue() != zipdata[i:]:
                print('start=%d end=None doesn\'t provide a good buffer' % i)
            f.close()

        for i in range(0, len(zipdata)):
            # all end positions with a fixed start position
            f = io.BytesIO()
            fp.writeStream(f, 0, i)
            if f.getvalue() != zipdata[:i]:
                print('start=0 end=%d doesn\'t provide a good buffer' % i)

        for i in range(100):
            # random start and end positions
            a = random.randrange(0, len(zipdata))
            b = random.randrange(0, len(zipdata))
            start = min(a, b)
            end = max(a, b)
            f = io.BytesIO()
            fp.writeStream(f, start, end)

if __name__ == '__main__':
    unittest.main()
