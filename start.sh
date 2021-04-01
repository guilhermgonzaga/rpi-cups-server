#!/usr/bin/env bash
# SPDX-License-Identifier: Unlicense
#
# Run with this script in case python-daemon gives
# problems (https://pagure.io/python-daemon/issue/50)

python3 -O ./controller.py & disown -h
