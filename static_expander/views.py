import mimetypes
import os
import stat
import urllib

from django import http, template
from django.conf import settings
from django.core.servers.basehttp import FileWrapper
from django.shortcuts import render_to_response
from django.utils.http import http_date
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy, ugettext as _
from django.contrib.auth.decorators import login_required


@login_required
def secure(request, url, document_root=None, perms=None, 
                 content_as_template=False, directory_index=('index.html'),
                 extensions=('.html'), base_template='expander/base.html'):

    """

    Serve static content but require the user to be logged in, this 

		url(r'^(?P<url>.*.html)$', 'static_expander.views.secure',
			 	{'document_root' : '/path/to/my/files/',
                 'directory_index' : ('index.html','index.htm'),
                 'extensions' : ('.html','.htm'),
                }),

    is the same as

		url(r'^(?P<url>.*.html)$', 
                login_required('static_expander.views.serve'),
			 	{'document_root' : '/path/to/my/files/',
                 'directory_index' : ('index.html','index.htm'),
                 'extensions' : ('.html','.htm'),
                }),

   
    Any of the decorators can be used in this fashion. The secure view
    is simply a convience function.

    This method does require that the "regiration/login.html" template
    exists and that LOGIN_URL and LOGIN_REDIRECT_URL be set in your
    settings file. You will also need to include the following in your
    URLconf: 

        (r'^accounts/login/$', 'django.contrib.auth.views.login'),


    """

    return serve(request, url, document_root, perms, content_as_template, 
                 directory_index, extensions, base_template)
 

# - Should probably make this honor the not modified since stuff.
def serve(request, url, document_root=None, perms=None, 
          content_as_template=False, directory_index=('index.html'),
          extensions=('.html'), base_template='expander/base.html'):
    """
	Serve static content wrapped inside of the sites template.

	To use, put a URL pattern such as: 

		url(r'^(?P<url>.*.html)$', 'static_expander.views.serve',
			 	{'document_root' : '/path/to/my/files/',
                 'directory_index' : ('index.html','index.htm'),
                 'extensions' : ('.html','.htm'),
                 'content_as_template' : True,
                 'perms' : ('can_add',)
                 'base_template': 'base.html'
                }),

	in your URLconf. The "document root" param must be provided, otherwise a
	404 error will be raised.

    If 'content_as_template' is set to true static content will be
    rendered as a template, rather than simply included.

    In order to make directory indexes work specify the valid index
    files in a list.

    Note: If your URLconf regex includes non-html files they will also
    be served by this method.

    """
    if document_root is None:
        raise http.Http404, '"%s" does not exist' % url

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
        raise http.Http404, '"%s" does not exist' % newpath

    fullpath = os.path.join(document_root, newpath)
    
    # Return a 404 if we don't exists
    try: 
        if not os.path.exists(fullpath):
            raise http.Http404, '"%s" does not exist' % fullpath
    except UnicodeEncodeError:
        raise http.Http404, '"%s" does not exist' % fullpath

    # If it's not a file then try adding default_page 
    if os.path.isdir(fullpath): 
        if url and not url.endswith('/') and settings.APPEND_SLASH:
            return http.HttpResponseRedirect("%s/" % request.path)

        realpath = None
        for part in directory_index:
            realpath = os.path.join(fullpath, part).replace('\\', '/')
            if os.path.isfile(realpath):
                break
        if realpath is not None:
            fullpath = realpath
   
    # Not a file or we can't read it.
    if not os.path.isfile(fullpath) or not os.access(fullpath, os.R_OK):
        raise http.Http404, '"%s" does not exist' % fullpath

    if os.path.splitext(fullpath)[1] not in extensions:
        # Serve file, don't let the whole thing into memory. 
        mimetype = mimetypes.guess_type(fullpath)[0] or 'application/octet-stream'

        wrapper = FileWrapper(file(fullpath))
        response = http.HttpResponse(wrapper, mimetype=mimetype)
        response["Last-Modified"] = http_date(os.path.getmtime(fullpath))
        response["Content-Length"] = os.path.getsize(fullpath)

        return response

    if content_as_template:
    # Finally, send the response to the user. This construct allows the
    # page to contain template directives. 
        t = template.Template("{%% extends \"%s\" %%}{%% block content %%}%s{%% endblock %%}" % (base_template, open(fullpath).read())) 
    
        return http.HttpResponse(t.render(template.RequestContext(request)))
    
    return render_to_response(base_template,
                              {'data': mark_safe(open(fullpath).read())},
                              context_instance=template.RequestContext(request))
