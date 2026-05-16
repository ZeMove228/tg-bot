#!/bin/bash
# Run this inside your bot folder (where bot.py and config.py are)

git init
git add bot.py config.py requirements.txt
git commit -m "first commit"
git remote add origin https://github.com/ZeMove228/tg-bot.git
git branch -M main
git push -u origin main
