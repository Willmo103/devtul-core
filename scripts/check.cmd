@echo off
echo ==========================================
echo Running BLACK (Formatter)
echo ==========================================
uv run black .
if %ERRORLEVEL% NEQ 0 goto :error

echo.
echo ==========================================
echo Running ISORT (Import Sorter)
echo ==========================================
uv run isort .
if %ERRORLEVEL% NEQ 0 goto :error

echo.
echo ==========================================
echo Running PYTEST (Unit Tests)
echo ==========================================
uv run pytest --cov=src --cov-report=html
if %ERRORLEVEL% NEQ 0 goto :error

echo.
echo ==========================================
echo SUCCESS: All checks passed.
echo ==========================================
exit /b 0

:error
echo.
echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
echo FAILED: Process stopped due to errors.
echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
exit /b %ERRORLEVEL%
