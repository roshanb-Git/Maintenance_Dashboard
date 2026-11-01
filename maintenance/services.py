from .models import Site

def allowed_sites(user):
    return Site.objects.all()
    