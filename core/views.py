from django.http import HttpResponse


def home(request):
	return HttpResponse("ERP uygulaması çalışıyor.")
