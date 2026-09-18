@echo off
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller pillow
python -m PyInstaller --onefile --noconsole --name "SilaStaliWindows" --icon "icon.ico" --add-data "logo.png;." --add-data "window_icon.png;." --add-data "module_laser.png;." --add-data "module_bender.png;." --add-data "module_mech.png;." --add-data "module_weld.png;." --add-data "module_store.png;." --add-data "module_laser_hub.png;." --add-data "module_bender_hub.png;." --add-data "module_mech_hub.png;." --add-data "module_weld_hub.png;." --add-data "module_store_hub.png;." --add-data "module_laser_square.png;." --add-data "module_bender_square.png;." --add-data "module_mech_square.png;." --add-data "module_weld_square.png;." --add-data "module_store_square.png;." --add-data "module_chief.png;." --add-data "module_chief_hub.png;." --add-data "module_chief_square.png;." --add-data "module_laser_grid.png;." --add-data "module_bender_grid.png;." --add-data "module_mech_grid.png;." --add-data "module_weld_grid.png;." --add-data "module_store_grid.png;." --add-data "module_chief_grid.png;." app.py
echo.
echo Exe собран: dist\SilaStaliWindows.exe
pause