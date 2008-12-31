import mimetypes
import os
import stat
import urllib

from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.utils.safestring import mark_safe
from django.utils.http import http_date

# Todo: 
# - Handle the auth correctly -- It does, just needs a login page now.
# - Should probably make this honor the not modified since stuff.
def serve(request, url, document_root=None, require_auth=False, perms=None, 
          directory_index=('index.html'), extensions=('.html')):
    """
	Serve static content wrapped inside of the sites template.

	To use, put a URL pattern such as: 

		url(r'^(?P<url>.*.html)$', 'expander.serve',
			 	{'document_root' : '/path/to/my/files/',
                 'directory_index' : ('index.html','index.htm')} 
                 'extensions' : ('.html','.htm')} 
			 	 'require_auth' : True,
                 'perms' : ('can_add',)},
                ),

	in your URLconf. The "document root" param must be provided, otherwise a
	404 error will be raised.

    In order to make directory indexes work specify the valid index
    files in a list.
    """
    if document_root is None:
        raise Http404, '"%s" does not exist' % url

    # Decode all the % ecoded stuff.
    path = os.path.normpath(urllib.unquote(url))
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
    if require_auth:
        if not request.user.is_authenticated():
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.path)
        elif perms is not None and not request.user.has_perms(perms):
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.path)

    # Return a 404 if we don't exists
    if not os.path.exists(fullpath):
        raise Http404, '"%s" does not exist' % fullpath

    # If it's not a file then try adding default_page 
    if os.path.isdir(fullpath): 
        if not url.endswith('/') and settings.APPEND_SLASH:
            return HttpResponseRedirect("%s/" % request.path)

        realpath = None
        for part in directory_index:
            realpath = os.path.join(fullpath, part).replace('\\', '/')
            if os.path.isfile(realpath):
                break
        if realpath is not None:
            fullpath = realpath
   
    # Not a file or we can't read it.
    if not os.path.isfile(fullpath) or not os.access(fullpath, os.R_OK):
        raise Http404, '"%s" does not exist' % fullpath

    if os.path.splitext(fullpath)[1] not in extensions:
        statobj = os.stat(fullpath)
        mimetype = mimetypes.guess_type(fullpath)[0] or 'application/octet-stream'
        contents = open(fullpath, 'rb').read()
        response = HttpResponse(contents, mimetype=mimetype)
        response["Last-Modified"] = http_date(statobj[stat.ST_MTIME])
        response["Content-Length"] = len(contents)
        return response

    # Finally, send the response to the user.
    return render_to_response( "expander/base.html", 
                               {'data': mark_safe(open(fullpath).read())} )
