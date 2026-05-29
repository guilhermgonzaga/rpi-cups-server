#!/usr/bin/env bash
# SPDX-License-Identifier: Unlicense

source venv/bin/activate
python3 -O ./controller.py & disown -h
