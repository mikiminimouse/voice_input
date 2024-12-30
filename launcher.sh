#!/bin/bash

# Минимально необходимые настройки окружения
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"

# Активируем виртуальное окружение
echo "=== Environment Variables ==="
echo "DCONF_PROFILE=$DCONF_PROFILE"
echo "GSETTINGS_SCHEMA_DIR=$GSETTINGS_SCHEMA_DIR"
echo "XDG_DATA_DIRS=$XDG_DATA_DIRS"
echo "DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS"
source venv/bin/activate

# Запускаем приложение
python3 main.py