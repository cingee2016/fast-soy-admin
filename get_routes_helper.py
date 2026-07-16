from fastapi import FastAPI
from fastapi.routing import APIRoute

def get_all_api_routes(router):
    routes = []
    for route in router.routes:
        if isinstance(route, APIRoute):
            routes.append(route)
        elif type(route).__name__ == '_IncludedRouter':
            routes.extend(get_all_api_routes(route.original_router))
        elif hasattr(route, 'routes'):
            routes.extend(get_all_api_routes(route))
    return routes
