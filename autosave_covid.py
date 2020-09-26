#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 17 17:35:10 2020

@author: amethyst
"""

import uwecscraper
import datetime
print('running autosave at {}'.format(datetime.datetime.now()))
uwecscraper.gather_and_save()

