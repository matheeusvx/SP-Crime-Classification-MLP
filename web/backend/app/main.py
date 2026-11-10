"""Aplicação FastAPI: só API, agregados e, opcionalmente, o build do frontend."""
from collections.abc import Callable
from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import Settings, load_settings
from .inference import ModelService, load_model_service, try_load
from .public_data import load_methodology, load_statistics
from .schemas import (ClassificacaoErro, ClassificacaoOk, ClassifyRequest, ErroServico, Estatisticas,
                      ModeloPublico, Opcoes, Saude)
from .security import SECURITY_HEADERS, BodySizeLimit, RateLimiter

logger = logging.getLogger('app')
FRONTEND_ROUTES = ('/', '/painel', '/sobre')
CACHE_PUBLICO = {'Cache-Control': 'public, max-age=3600'}
MSG_MODELO = 'O classificador está temporariamente indisponível. Nenhuma classificação foi gerada.'
MSG_DADOS = 'As estatísticas agregadas não estão disponíveis no momento.'


class RateLimited(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


def indisponivel(mensagem: str) -> JSONResponse:
    return JSONResponse(status_code=503, content={'status': 'servico_indisponivel', 'mensagem': mensagem})


def create_app(settings: Settings | None = None,
               service_factory: Callable[[], ModelService] | None = None) -> FastAPI:
    settings = settings or load_settings()
    factory = service_factory or (lambda: load_model_service(settings.model_dir))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = try_load(factory)  # uma única carga por processo
        app.state.statistics = load_statistics(settings.data_dir)
        app.state.methodology = load_methodology(settings.data_dir)
        yield

    docs = {'docs_url': '/api/docs', 'openapi_url': '/api/openapi.json'} if settings.expose_docs else \
           {'docs_url': None, 'openapi_url': None}
    app = FastAPI(title='Classificador acadêmico FURTO × ROUBO — GS FIAP', version=__version__,
                  redoc_url=None, lifespan=lifespan, **docs)
    limiter = RateLimiter(settings.rate_limit_per_minute)

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=False,
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
    app.add_middleware(BodySizeLimit, max_bytes=settings.max_body_bytes)

    @app.middleware('http')
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        if not (settings.expose_docs and request.url.path.startswith('/api/docs')):
            for name, value in SECURITY_HEADERS.items():
                response.headers.setdefault(name, value)
        return response

    @app.exception_handler(RateLimited)
    async def on_rate_limited(_: Request, exc: RateLimited):
        return JSONResponse(status_code=429, headers={'Retry-After': str(exc.retry_after)},
                            content={'status': 'limite_excedido',
                                     'mensagem': 'Muitas classificações em pouco tempo. Aguarde e tente novamente.'})

    def schema_error(request: Request) -> JSONResponse:
        # Chaves ausentes/extras ou corpo ilegível: a resposta vem do próprio contrato.
        service: ModelService | None = request.app.state.service
        if service is None:
            return indisponivel(MSG_MODELO)
        return JSONResponse(status_code=422, content=service.classify({}))

    @app.exception_handler(RequestValidationError)
    async def on_schema_error(request: Request, _: RequestValidationError):
        return schema_error(request)

    @app.exception_handler(StarletteHTTPException)
    async def on_http_error(request: Request, exc: StarletteHTTPException):
        # FastAPI responde 400 quando os bytes do corpo não são UTF-8 decodificável.
        if exc.status_code == 400 and request.url.path == '/api/classify':
            return schema_error(request)
        return await http_exception_handler(request, exc)

    def rate_limit(request: Request) -> None:
        client = request.client.host if request.client else 'desconhecido'
        retry = limiter.retry_after(client)
        if retry is not None:
            raise RateLimited(retry)

    @app.get('/api/health', response_model=Saude, responses={503: {'model': Saude}})
    def health(request: Request):
        loaded = request.app.state.service is not None
        stats = request.app.state.statistics is not None
        body = {'status': 'ok' if loaded and stats else 'indisponivel', 'modelo_carregado': loaded,
                'estatisticas_carregadas': stats, 'versao_api': __version__}
        return JSONResponse(status_code=200 if body['status'] == 'ok' else 503, content=body)

    @app.get('/api/model', response_model=ModeloPublico, responses={503: {'model': ErroServico}})
    def model(request: Request):
        service: ModelService | None = request.app.state.service
        return service.public_metadata() if service else indisponivel(MSG_MODELO)

    @app.get('/api/options', response_model=Opcoes, responses={503: {'model': ErroServico}})
    def options(request: Request):
        service: ModelService | None = request.app.state.service
        return JSONResponse(service.options(), headers=CACHE_PUBLICO) if service else indisponivel(MSG_MODELO)

    @app.post('/api/classify', response_model=ClassificacaoOk, dependencies=[Depends(rate_limit)],
              responses={422: {'model': ClassificacaoErro}, 429: {'model': ErroServico},
                         503: {'model': ErroServico}})
    def classify(payload: ClassifyRequest, request: Request):
        service: ModelService | None = request.app.state.service
        if service is None:
            return indisponivel(MSG_MODELO)
        try:
            result = service.classify(payload.model_dump())
        except Exception:
            # O registro enviado não vai para o log.
            logger.error('Falha interna na inferência.')
            return indisponivel(MSG_MODELO)
        if result['status'] != 'ok':
            return JSONResponse(status_code=422, content=result)
        return result

    @app.get('/api/statistics', response_model=Estatisticas, responses={503: {'model': ErroServico}})
    def statistics(request: Request):
        data = request.app.state.statistics
        return JSONResponse(data, headers=CACHE_PUBLICO) if data else indisponivel(MSG_DADOS)

    @app.get('/api/methodology', responses={503: {'model': ErroServico}})
    def methodology(request: Request):
        data = request.app.state.methodology
        return JSONResponse(data, headers=CACHE_PUBLICO) if data else indisponivel(MSG_DADOS)

    if settings.frontend_dist:
        dist = settings.frontend_dist
        app.mount('/assets', StaticFiles(directory=dist/'assets'), name='assets')

        def index():
            return FileResponse(dist/'index.html', headers={'Cache-Control': 'no-cache'})
        for route in FRONTEND_ROUTES:
            app.add_api_route(route, index, include_in_schema=False)
        if (dist/'favicon.svg').is_file():
            app.add_api_route('/favicon.svg', lambda: FileResponse(dist/'favicon.svg'), include_in_schema=False)

    return app


logging.basicConfig(level=logging.INFO)
app = create_app()
