import mimetypes
import os
import stat
import urllib

from django import http, template
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.servers.basehttp import FileWrapper
from django.shortcuts import render_to_response
from django.utils.http import http_date
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy, ugettext as _

ERROR_MESSAGE = ugettext_lazy("Please enter a correct username and password. Note that both fields are case-sensitive.")
LOGIN_FORM_KEY = 'this_is_the_login_form'

# _checklogin Based on _checklogin from django.contrib.admin.views.decorators
def _checklogin(request, perms):
    def _display_login_form(request, error_message=''):
        request.session.set_test_cookie()
        
        return render_to_response('expander/login.html', {
            'title': _('Log in'),
            'app_path': request.get_full_path(),
            'error_message': error_message
            }, context_instance=template.RequestContext(request))

    # If this isn't already the login page, display it.
    if LOGIN_FORM_KEY not in request.POST:
        if request.POST:
            message = _("Please log in again, because your session has expired.")
        else:
            message = ""
        return _display_login_form(request, message)

    # Check that the user accepts cookies.
    if not request.session.test_cookie_worked():
        message = _("Looks like your browser isn't configured to accept cookies. Please enable cookies, reload this page, and try again.")
        return _display_login_form(request, message)
    else:
        request.session.delete_test_cookie()

    # Check the password.
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)
    user = authenticate(username=username, password=password)

    if user is None:
        return _display_login_form(request, ERROR_MESSAGE)
    elif user.is_active and perms is None:
        login(request, user)
        return http.HttpResponseRedirect(request.get_full_path())
    elif user.is_active and perms and not request.user.has_perms(perms):
        login(request, user)
        return http.HttpResponseRedirect(request.get_full_path())
    else:
        return _display_login_form(request, ERROR_MESSAGE)

# - Should probably make this honor the not modified since stuff.
def serve(request, url, document_root=None, require_auth=False, perms=None, 
          content_as_template=False, directory_index=('index.html'),
          extensions=('.html'), base_template='expander/base.html'):
    """
	Serve static content wrapped inside of the sites template.

	To use, put a URL pattern such as: 

		url(r'^(?P<url>.*.html)$', 'static_expander.views.serve',
			 	{'document_root' : '/path/to/my/files/',
                 'directory_index' : ('index.html','index.htm'),
                 'extensions' : ('.html','.htm'),
			 	 'require_auth' : True,
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

		url(r'^(?P<url>.*.html)$', 
                login_required(static_expander.views.serve),
			 	{'document_root' : '/path/to/my/files/',
                 'directory_index' : ('index.html','index.htm'),
                 'extensions' : ('.html','.htm'),
                 'content_as_template' : True,
                 'base_template': 'base.html'
                }),

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
    
    # Send to auth if we require auth and not authenticated.
    if require_auth:
        if not request.user.is_authenticated():
            return _checklogin(request, perms)
        elif perms and not request.user.has_perms(perms):
            return _checklogin(request, perms)

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
