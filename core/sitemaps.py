from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import LabService

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['home-page', 'index-page', 'about-us', 'info-page', 'terms-of-use', 'privacy-policy', 'global-doctor-directory']

    def location(self, item):
        return reverse(item)