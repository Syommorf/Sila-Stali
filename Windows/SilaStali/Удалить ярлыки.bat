@echo off
rem =====================================================
rem  Удаление ярлыков "Сила стали"
rem =====================================================
powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item ([Environment]::GetFolderPath('Desktop') + '\Сила стали.lnk') -ErrorAction SilentlyContinue; Remove-Item ([Environment]::GetFolderPath('Programs') + '\Сила стали.lnk') -ErrorAction SilentlyContinue"
echo Ярлыки удалены.
pause