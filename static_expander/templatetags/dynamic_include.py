import os, stat, urllib

from django import template
from django.conf import settings

# {% include "/path/to/file" %} From the document root.
# {% include "relative.html" %} From current dir to document root.

class DynamicIncludeNode(template.Node):
    def __init__(self, path):
        self.path = path
    def render(self, context):
        """ Open and read the file """ 
        # settings.DOCUMENT_ROOT
        # context.
    
        path = os.path.normpath(urllib.unquote(self.path))
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
    
        if newpath and path != newpath:
            if settings.DEBUG:
                return "[Invalid include file]"
            else:
                return '' # Fail Silently, Does not exist.
        
        fullpath = os.path.join(document_root, newpath)
    
        if self.path[0] == '/':
            # Should we even do this? Force people to use {% ssi ... %}
            fullpath = os.path.join(document_root, newpath)
            if os.path.exists(fullpath):
                try:
                    fp = open(fullpath, 'r')
                    output = fp.read()
                    fp.close()
                except IOError:
                    output = ''
                return output
        else:

            # Walk the directory including till we get to root...
            # What is the current url ?
            #current_path = template.resolve_variable('request.path', context)

            return self.path

#@register.tag
def dynamic_include(parser, token):
    """
    Loads a file and renders it with the current context. Requires the
    DOCUMENT_ROOT variable be set to the document root for the site.

    Example::

        {% dynamic_include /path/from/document_root %}
        {% dynamic_include relative_to_current_url.html %}
    """
    bits = token.contents.split()
    if ! settings.DOCUMENT_ROOT:
        raise template.TemplateSyntaxError, "%r tag requires DOCUMENT_ROOT variable be defined in settings.py" % bits[0]
    if len(bits) != 2:
        raise template.TemplateSyntaxError, "%r tag requires a single argument: the name of the file to be included" % bits[0]
    return DynamicIncludeNode(bits[1])
dynamic_include = register.tag(dynamic_include)
