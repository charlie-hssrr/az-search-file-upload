#!/bin/sh

echo 'Creating python virtual environment ".venv"'
python3 -m venv .venv

echo ""
echo "Restoring backend python packages"
echo ""

cd .venv/
./bin/python -m pip install -r ../requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to restore backend python packages"
    exit $?
fi

echo ""
echo "Starting server"
echo ""

cd ..

port=60666
host=localhost
.venv/bin/python -m quart --app main:app run --port "$port" --host "$host" --reload
if [ $? -ne 0 ]; then
    echo "Failed to start server"
    exit $?
fi
