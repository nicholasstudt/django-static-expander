import os
import stat
import urllib

from django import template
from django.template import TemplateSyntaxError
from django.conf import settings

register = template.Library()

class DynamicIncludeNode(template.Node):

    def __init__(self, include_file, no_recurse = None, var_name = None):
        self.include_file = include_file
        self.no_recurse = no_recurse
        self.var_name = var_name

    def render(self, context):
        """ Open and read the file, after we work it out... """ 
        document_root = settings.DOCUMENT_ROOT
    
        path = os.path.normpath(urllib.unquote(self.include_file))
        path = path.lstrip('/')
        include = ''
        for part in path.split('/'):
            if not part:
                # Strip empty path components.
                continue
            drive, part = os.path.splitdrive(part)
            head, part = os.path.split(part)
            if part in (os.curdir, os.pardir):
                # Strip '.' and '..' in path.
                continue
            include = os.path.join(include, part).replace('\\', '/')
    
        if include and path != include:
            if settings.DEBUG:
                return "[Invalid include file]"
            else:
                return '' # Fail Silently, Does not exist.
        
        if self.include_file[0] == '/':
            # Should we even do this? Force people to use {% ssi ... %}
            fullpath = os.path.join(document_root, include)
            if not os.path.exists(fullpath):
                fullpath = ''
        else:
            try: 
                request = template.resolve_variable('request', context)
            except Exception:
                if settings.DEBUG:
                    return "[django.core.context_processors.request not included in TEMPLATE_CONTEXT_PROCESSORS in settings.py]"
                else:
                    return '' # Fail Silently, we don't have context
 
            # If request.path is a directory use it, or remove file
            if os.path.isdir(str.join(os.sep, (document_root, request.path))):
                test_path = request.path.lstrip('/').rstrip('/') 
            else: 
                test_path = os.path.dirname(request.path).lstrip('/')

            parts = test_path.split('/')

            # Walk the directory including till we get to root...
            # Unless the no_recurse flag is !None
            try:
                while parts and not self.no_recurse and not os.access(str.join(os.sep, (document_root, test_path, include)), os.R_OK):
                    parts = parts[0:-1] # Shrink parts by 1
                    test_path = str.join(os.sep, parts)
            except UnicodeEncodeError:
                test_path = ''

            fullpath = str.join(os.sep, (document_root, test_path, include, ))

        try:
            fp = open(fullpath, 'r')
            output = fp.read()
            fp.close()
        except IOError:
            output = ''
    
        # Add to the page context if requested and has output
        if self.var_name and output:

            context[self.var_name] = mark_safe(output)

            return ''

        return output

#@register.tag
def dynamic_include(parser, token):
    """
    Loads a file and renders it with the current context. Requires the
    DOCUMENT_ROOT variable be set to the document root for the site.

    To use the second form, relative to the current url you must adjust
    the TEMPLATE_CONTEXT_PROCESSORS in settings.py to include
    'django.core.context_processors.request' or relative includes will
    not work.

    Example::

        {% dynamic_include /path/from/document_root [no_recurse] [as var_name] %}
        {% dynamic_include relative_to_current_url.html [no_recurse] [as var_name] %}
    """
    bits = token.contents.split()
    if not settings.DOCUMENT_ROOT:
        raise template.TemplateSyntaxError, "%r tag requires DOCUMENT_ROOT variable be defined in settings.py" % bits[0]

    no_recurse = None
    var_name = None

    # Check that we have enough arguments and not too many
    if len(bits) < 2:
        raise template.TemplateSyntaxError, "%r tag requires at least a single argument: the name of the file to be included" % bits[0]

    if len(bits) > 5:
        raise template.TemplateSyntaxError, "%r tag must have no more than four arguments" % bits[0]

    # Check for the no_recurse flag only
    if len(bits) == 3:
        no_recurse = True

    # Check for both no_recurse and "as var_name"
    if len(bits) > 3:
        if bits[2].lower() == 'as':
            var_name = bits[3]
            #If there is an extra arg, then assume no_recurse is set.
            if len(bits) == 5:
                no_recurse = True
        else:
            no_recurse = True
            if not bits[3].lower() == 'as':
                raise template.TemplateSyntaxError, "If %r tag has more than two arguments, it must include the \"as var_name\" argument" % bits[0]
            var_name = bits[4]
    
    return DynamicIncludeNode(bits[1], no_recurse = no_recurse, var_name = var_name)
dynamic_include = register.tag(dynamic_include)
