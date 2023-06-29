import logging
from django.shortcuts import render

class ErrorHandlerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Exception as e:
            logging.error(str(e))  # Log the error
            response = self.handle_error(request, e)
        return response

    def handle_error(self, request, exception):
        # Perform custom error handling here
        return render(request, 'home.html', status=500)