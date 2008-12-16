from django.http import Http404
from django.shortcuts import render_to_response

BASE_XPANDER_PATH = "/where/ever/"

def xpander(request, url):
   
    # url should be checked to verify it does not contain ".." in any
    # form.
    fname = os.path.join(BASE_XPANDER_PATH, url)

    # os.path.normpath(fname) # Works out the name removing ../../ and like

    if not os.path.exists(fname):
        raise Http404
    else:
        return render_to_response( "some/template.html", 
                                    {'data': open(fname).read()}
                                    )
