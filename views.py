import os
import posixpath
import urllib

from django.http import Http404
from django.shortcuts import render_to_response
from django.utils.safestring import mark_safe

# Todo: 
# - Handle the auth correctly.
# - Make it deal with the default page (index.htm/l) correctly. 

def serve(request, url, document_root=None, require_auth=False):
    """
	Serve static content wrapped inside of the sites template.

	To use, put a URL pattern such as: 

		url(r'^(?P<url>.*.html)$', 'expander.serve',
			 	{'document_root' : '/path/to/my/files/'}),

    or

		url(r'^(?P<url>.*.html)$', 'expander.serve',
			 	{'document_root' : '/path/to/my/files/',
			 	'require_auth' : True }),

	in your URLconf. The "document root" param must be provided, otherwise a
	404 error will be raised.
    """
    if document_root is None:
        raise Http404, '"%s" does not exist' % url

    # Decode all the % ecoded stuff.
    path = posixpath.normpath(urllib.unquote(url))
    path = path.lstrip('/')
    newpath = ''
    for part in path.split('/'):
        if not part:
            # Strip empty path components.
            continue
        drive, part = os.path.splitdrive(part)
        head, part = os.path.split(part)
        if part in (os.curdir, os.pardir):
            # Strip '.' and '..' in path.
            continue
        newpath = os.path.join(newpath, part).replace('\\', '/')
    
    # Return a 404 if the path contains a "/../"
    if newpath and path != newpath:
        raise Http404, '"%s" does not exist' % newpath

    fullpath = os.path.join(document_root, newpath)
    
    # Send to auth if we require auth and not authenticated.
    if require_auth and not request.user.is_authenticated():
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.path)

    # Return a 404 if we don't exists
    if not os.path.exists(fullpath):
        raise Http404, '"%s" does not exist' % fullpath

    # If it's not a file then try adding default_page 
    if not os.path.isfile(fullpath):
        raise Http404, '"%s" does not exist' % fullpath

    if not os.access(fullpath, os.R_OK):
        raise Http404, '"%s" does not exist' % fullpath

    # Finally, send the response to the user.
    return render_to_response( "expander/base.html", 
                                {'data': mark_safe(open(fullpath).read())} )
