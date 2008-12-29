import urllib

from django.http import Http404
from django.shortcuts import render_to_response


BASE_XPANDER_PATH = "/where/ever/"

# ALLOWED_INCLUDE_ROOTS <-- Require document root to be in this ?
# Use MEDIA_ROOT as DOCUMENT_ROOT ?

def serve(request, url, document_root=None):
	"""
	Serve static content wrapped inside of the sites template.

	To use, put a URL pattern such as: 

		url(r'^(?P<path>.*.html)$', 'expander.serve',
			 	{'document_root' : '/path/to/my/files/'})

	in your URLconf. The "document root" param must be provided, otherwise a
	404 error will be raised.
	"""

	if document_root is None:
		raise Http404, '"%s" does not exist' % fullpath

	# Decode all he % ecoded stuff.
	newurl = urllib.unquote(url)
	# Has this already been done to the URL ?

	# Return a 404 if the path contains a "/../"
   
    # url should be checked to verify it does not contain ".." in any
    # form.
    fname = os.path.join(document_root, url)

    # os.path.normpath(fname) # Works out the name removing ../../ and like


    if not os.path.exists(fname):
        raise Http404
    else:
        return render_to_response( "expander/base.html", 
                                    {'data': open(fname).read()}
                                    )
