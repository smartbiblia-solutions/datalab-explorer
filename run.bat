@ECHO OFF
::admin/admin@admin
set mypath=%cd%

docker compose up -d --force-recreate

ECHO ============================
ECHO Container running...

ECHO ============================
PAUSE