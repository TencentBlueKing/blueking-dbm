# -*- coding: utf-8 -*-

#: List containing string constant that are used to represent headers that can
#: be ignored in the required_header function
IGNORE_HEADERS = (
    "HTTP_ACCEPT_ENCODING",  # We want content to be uncompressed so
    # we remove the Accept-Encoding from
    # original request
    "HTTP_HOST",
    "HTTP_REMOTE_USER",
)


def required_header(header):
    """Function that verify if the header parameter is a essential header

    :param header:  A string represented a header
    :returns:       A boolean value that represent if the header is required
    """
    if header in IGNORE_HEADERS:
        return False

    if header.startswith("HTTP_") or header == "CONTENT_TYPE":
        return True

    return False


def normalize_request_headers(request):
    """Function used to transform header, replacing 'HTTP_' to ''
    and replace '_' to '-'
    :param request:  A HttpRequest that will be transformed
    :returns:        A dictionary with the normalized headers
    """
    norm_headers = {}
    for header, value in request.META.items():
        if required_header(header):
            norm_header = header.replace("HTTP_", "").title().replace("_", "-")
            norm_headers[norm_header] = value

    return norm_headers
