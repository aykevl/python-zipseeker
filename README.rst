Zip file streamer for HTTP
==========================

Similar systems/projects:

* The `Nginx zip module
  <https://www.nginx.com/resources/wiki/modules/zip/>`_. Only for Nginx, so
  can't be used with other webservers.
* `python-zipstream <https://github.com/allanlei/python-zipstream>`_. Does not
  support calculating the file size beforehand or seeing through the file.

Usage:

.. code:: python

    import zipseeker
    
    # Create an index
    fp = zipseeker.ZipSeeker()
    fp.add('some/file.txt')
    fp.add('another/file.txt', 'file2.txt')
    
    # Calculate the total file size, e.g. for the Content-Length HTTP header.
    contentLength = fp.size()
    
    # Calculate the last-modified date, e.g. for the Last-Modified HTTP header.
    lastModified = fp.lastModified()
    
    # Send the ZIP file to the client
    # Optionally add the start and end parameters for range requests.
    # Note that the ZIP format doesn't support actually skipping parts of the file,
    # as it needs to calculate the CRC-32 of every file at the end of the file.
    fp.writeStream(outputFile)

Why?
----

While the file size of a ZIP file usually can't be calculated beforehand due to
compression, this is actually optional. The headers itself also have a pretty
constant size. That means that the whole file can have a predetermined file size
(and modtime).

This is useful when you want to provide ZIP downloads of large directories with
uncompressable files (e.g. images). The specific use case I created this media
file for was to provide downloads of whole photo albums without such
inconveniences as requesting a downloading link in an e-mail, using a lot system
resources for the creation of temporary files, and having to delete these files
afterwards.

Of course, it's possible to just stream a ZIP file, but that won't provide any
progress indication for file downloads and certainly doesn't support `Range
requests <https://developer.mozilla.org/en-US/docs/Web/HTTP/Range_requests>`_.

For more information, see the `Nginx zip module
<https://www.nginx.com/resources/wiki/modules/zip/>`_.

TODO
----

* Implement actual seeking in the file - this should be doable.
* Use a CRC-32 cache that can be shared by the calling module.

