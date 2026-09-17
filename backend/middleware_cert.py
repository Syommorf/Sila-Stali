from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from config import APK_CERT_HASHES

_CERT_HEADER = "X-APK-Cert"
_SKIP_PATHS = {"/health", "/app/update", "/apk/", "/docs", "/openapi.json", "/redoc"}


class CertMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if not any(path == p or path.startswith(p) for p in _SKIP_PATHS):
            cert = request.headers.get(_CERT_HEADER, "")
            # Отсутствие заголовка = Windows-десктоп (без сертификата) — пропускаем.
            # Неверный отпечаток = скопированный/пересобранный APK — блокируем.
            if cert and cert.lower() not in APK_CERT_HASHES:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Неавторизованная копия приложения"},
                )
        return await call_next(request)