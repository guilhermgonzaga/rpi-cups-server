#!/usr/bin/env bash
# Run with this script in case python-daemon gives
# problems (https://pagure.io/python-daemon/issue/50)

python -O ./controller.py & disown -h
