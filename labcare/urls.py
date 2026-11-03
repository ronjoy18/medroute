from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap
from core.views import robots_txt
from django.http import HttpResponse


sitemaps = {
    'static': StaticViewSitemap,
}

def sitemap_xml(request):
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://medrouterrands.com/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://medrouterrands.com/connect-care-giver/</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://medrouterrands.com/about-us/</loc>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>"""
    return HttpResponse(xml_content, content_type="application/xml")
    
def robots_txt(request):
    content = "User-agent: *\nAllow: /\n"
    return HttpResponse(content, content_type="text/plain")
    
urlpatterns = [
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),

    path("admin/", admin.site.urls),
    #path("secure/management-portal/", admin.site.urls),  # Keep alias if desired
    path("", include("core.urls")),
]
 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

def trigger_error(request):
  division_by_zero = 1 / 0

urlpatterns += [
    path('sentry-debug/', trigger_error),
]