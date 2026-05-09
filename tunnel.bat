@echo off
title ISP Manager Tunnel
echo ====================================
echo INICIANDO TUNNEL PUBLICO
echo ====================================
npx --yes localtunnel --port 5000 --subdomain isp-manager-app
echo.
echo TU URL ES: https://isp-manager-app.loca.lt
echo.
pause