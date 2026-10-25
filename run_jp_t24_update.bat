@echo off
:: Forwarding wrapper to standardized run_jp_t24.bat
call "%~dp0run_jp_t24.bat" %*
exit /b %ERRORLEVEL%
