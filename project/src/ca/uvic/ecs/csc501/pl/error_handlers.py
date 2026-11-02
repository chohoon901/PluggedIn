from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from ca.uvic.ecs.csc501.cmn.contracts.errors import AppError
from .views import render, validation_fields


def error_response(request, message, code, status_code, field_errors=None):
    fields = field_errors or {}
    if request.url.path.startswith('/api/'):
        return JSONResponse({'error': {'code': code, 'message': message, 'field_errors': fields}}, status_code=status_code)
    return render(request, 'errors/error.html', {'message': message, 'code': code, 'errors': fields, 'status_code': status_code}, status_code)


def register_error_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    def app_error(request: Request, exc: AppError):
        return error_response(request, exc.message, exc.code, exc.status_code, exc.field_errors)

    @app.exception_handler(RequestValidationError)
    def invalid_request(request: Request, exc: RequestValidationError):
        return error_response(request, 'Please check your entries.', 'INVALID_INPUT', 400, validation_fields(exc))

    @app.exception_handler(HTTPException)
    def http_error(request: Request, exc: HTTPException):
        return error_response(request, str(exc.detail), 'NOT_FOUND' if exc.status_code == 404 else 'HTTP_ERROR', exc.status_code)

    @app.exception_handler(Exception)
    def unexpected(request: Request, exc: Exception):
        return error_response(request, 'We could not complete this request. Please try again.', 'INTERNAL_ERROR', 500)
