import os
import stat
import urllib

from django import template
from django.template import TemplateSyntaxError
from django.conf import settings

register = template.Library()

class DynamicIncludeNode(template.Node):
    def __init__(self, include_file):
        self.include_file = include_file
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
 
            test_path = request.path.lstrip('/').rstrip('/')
            parts = test_path.split('/')

            # Walk the directory including till we get to root...
            while not parts and not os.access(str.join(os.sep, (document_root, test_path, include)), os.R_OK):
                parts = parts[0:-1] # Shrink parts by 1
                test_path = str.join(os.sep, parts)

            fullpath = str.join(os.sep, (document_root, test_path, include, ))

        try:
            fp = open(fullpath, 'r')
            output = fp.read()
            fp.close()
        except IOError:
            output = ''
        
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

        {% dynamic_include /path/from/document_root %}
        {% dynamic_include relative_to_current_url.html %}
    """
    bits = token.contents.split()
    if not settings.DOCUMENT_ROOT:
        raise template.TemplateSyntaxError, "%r tag requires DOCUMENT_ROOT variable be defined in settings.py" % bits[0]
    if len(bits) != 2:
        raise template.TemplateSyntaxError, "%r tag requires a single argument: the name of the file to be included" % bits[0]
    return DynamicIncludeNode(bits[1])
dynamic_include = register.tag(dynamic_include)
