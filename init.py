#!/bin/bash
from navibot import NaviBot

if __name__ == "__main__":
	bot = NaviBot("release/config.json")
	bot.rodar()
	