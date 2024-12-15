from django.utils.deprecation import MiddlewareMixin

class RequestCityMiddleware(MiddlewareMixin):
    """
    Middleware to persist the 'city' parameter across requests.
    The 'city' parameter is extracted from the request path and saved
    to the session or a custom request attribute.
    """
    def process_view(self, request, view_func, view_args, view_kwargs):
        city = view_kwargs.get('city')
        if city:
            request.session['city'] = city
            request.city = city
        else:
            city = request.session.get('city')
            if city:
                request.city = city
        return None
