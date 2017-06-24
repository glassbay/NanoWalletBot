#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# RaiBlocks Telegram bot
# @RaiWalletBot https://t.me/RaiWalletBot
# 
# Source code:
# https://github.com/SergiySW/RaiWalletBot
# 
# Released under the BSD 3-Clause License
# 
# 
# Run by cron every minute
# 

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Bot, ParseMode
import logging
import urllib3, certifi, socket, json
import time, math

# Parse config
import ConfigParser
config = ConfigParser.ConfigParser()
config.read('bot.cfg')
api_key = config.get('main', 'api_key')

# MySQL requests
from common_mysql import *



# Common functions
from common import push, mrai_text


# Translation
with open('language.json') as lang_file:    
	language = json.load(lang_file)
def lang_text(text_id, lang_id):
	try:
		return language[lang_id][text_id]
	except KeyError:
		return language['en'][text_id]

BLACK_LIST = mysql_select_blacklist()

def mercatox():
	http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',ca_certs=certifi.where())
	url = 'https://mercatox.com/public/json24'
	response = http.request('GET', url)
	json_mercatox = json.loads(response.data)
	json_array = json_mercatox['pairs']['XRB_BTC']
	try:
		last_price = int(float(json_array['last']) * (10 ** 8))
	except KeyError:
		last_price = 0
	high_price = int(float(json_array['high24hr']) * (10 ** 8))
	low_price = int(float(json_array['low24hr']) * (10 ** 8))
	ask_price = int(float(json_array['lowestAsk']) * (10 ** 8))
	bid_price = int(float(json_array['highestBid']) * (10 ** 8))
	volume = int(float(json_array['baseVolume']))
	btc_volume = int(float(json_array['quoteVolume']) * (10 ** 8))
	
	mysql_set_price(1, last_price, high_price, low_price, ask_price, bid_price, volume, btc_volume)


def bitgrail():
	http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',ca_certs=certifi.where())
	url = 'https://bitgrail.com/api/v1/BTC-XRB/ticker'
	response = http.request('GET', url)
	json_bitgrail = json.loads(response.data)
	json_array = json_bitgrail['response']
	last_price = int(float(json_array['last']) * (10 ** 8))
	high_price = int(float(json_array['high']) * (10 ** 8))
	low_price = int(float(json_array['low']) * (10 ** 8))
	ask_price = int(float(json_array['ask']) * (10 ** 8))
	bid_price = int(float(json_array['bid']) * (10 ** 8))
	volume = int(float(json_array['coinVolume']))
	btc_volume = int(float(json_array['volume']) * (10 ** 8))
	
	mysql_set_price(2, last_price, high_price, low_price, ask_price, bid_price, volume, btc_volume)


def prices_above_below(bot, user_id, price, exchange, above = 1):
	lang_id = mysql_select_language(user_id)
	btc_price = ('%.8f' % (float(price) / (10 ** 8)))
	if (user_id not in BLACK_LIST):
		mysql_set_blacklist(user_id)
		if (above == 1):
			text = lang_text('prices_above', lang_id).format(exchange, btc_price)
		else:
			text = lang_text('prices_below', lang_id).format(exchange, btc_price)
		push(bot, user_id, text)
		print(text)
		mysql_delete_blacklist(user_id) # if someone deleted chat, broadcast will fail and he will remain in blacklist
		if (above == 1):
			mysql_delete_price_high(user_id)
		else:
			mysql_delete_price_low(user_id)
		time.sleep(0.5)


def price_check():
	bot = Bot(api_key)
	price = mysql_select_price()
	users_high = mysql_select_price_high()
	users_low = mysql_select_price_low()
	# check if higher
	for user in users_high:
		if ((int(price[1][1]) >= int(user[1])) and ((int(user[2]) == 0) or (int(user[2]) == 1))):
			prices_above_below(bot, user[0], price[1][1], "BitGrail.com")
		elif ((int(price[0][1]) >= int(user[1])) and ((int(user[2]) == 0) or (int(user[2]) == 2))):
			prices_above_below(bot, user[0], price[0][1], "Mercatox.com")
	# check if lower
	for user in users_low:
		if ((int(price[1][2]) <= int(user[1])) and ((int(user[2]) == 0) or (int(user[2]) == 1))):
			prices_above_below(bot, user[0], price[1][2], "BitGrail.com", 0)
		elif ((int(price[0][2]) <= int(user[1])) and ((int(user[2]) == 0) or (int(user[2]) == 2))):
			prices_above_below(bot, user[0], price[0][2], "Mercatox.com", 0)

def prices_usual():
	try:
		mercatox()
	except:
		time.sleep(1) # too many errors from Mercatox API
	try:
		bitgrail()
	except:
		time.sleep(5)
		bitgrail()
	
	price_check()


time.sleep(15)
prices_usual()
