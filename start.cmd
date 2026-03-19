@echo off
chcp 65001 >nul 2>&1
title OrwellRU - Claude Code

:: Переход в папку проекта
cd /d "%~dp0"

:: Запуск Claude Code в рабочей директории
claude --model opus --permission-mode bypassPermissions --verbose --debug

pause
