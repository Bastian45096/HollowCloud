# apps/common/middleware.py
import time
import logging
from django.db import connection

logger = logging.getLogger(__name__)

class TimingMiddleware:
    """
    Middleware para medir el tiempo total de respuesta y las consultas SQL.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Iniciar contadores
        start_time = time.time()
        start_queries = len(connection.queries)

        # Procesar la petición
        response = self.get_response(request)

        # Calcular duración
        duration_ms = (time.time() - start_time) * 1000
        query_count = len(connection.queries) - start_queries

        # Mostrar en consola (usando logger o print)
        logger.info(
            f"[TIMING] {request.method} {request.path} | "
            f"Total: {duration_ms:.2f}ms | Queries: {query_count}"
        )

        # Opcional: agregar cabeceras HTTP (como xbench)
        response['X-Total-Time'] = f"{duration_ms:.2f}ms"
        response['X-Query-Count'] = str(query_count)

        return response