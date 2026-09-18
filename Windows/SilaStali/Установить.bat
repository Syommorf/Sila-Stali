@echo off
rem =====================================================
rem  Установка "Сила стали" (Windows)
rem  Создаёт ярлыки на рабочем столе и в меню "Пуск"
rem =====================================================
cd /d "%~dp0"
if not exist "%~dp0Сила стали.exe" (
    echo Ошибка: файл "Сила стали.exe" не найден.
    echo Убедитесь, что программа лежит рядом с этим файлом.
    pause
    exit /b 1
)
set "EXE=%~dp0Сила стали.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $lnk = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Сила стали.lnk'); $lnk.TargetPath = $env:EXE; $lnk.WorkingDirectory = Split-Path $env:EXE; $lnk.IconLocation = $env:EXE + ',0'; $lnk.Save(); $d = [Environment]::GetFolderPath('Programs') + '\Сила стали.lnk'; $lnk2 = $ws.CreateShortcut($d); $lnk2.TargetPath = $env:EXE; $lnk2.WorkingDirectory = Split-Path $env:EXE; $lnk2.IconLocation = $env:EXE + ',0'; $lnk2.Save()"
echo.
echo Готово! Ярлыки созданы:
echo   - Рабочий стол: Сила стали
echo   - Меню Пуск:    Сила стали
echo.
echo Запускайте программу ярлыком или файлом "Сила стали.exe".
echo.
pause