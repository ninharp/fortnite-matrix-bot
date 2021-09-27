#!/bin/sh -e

eval "$( while read -r l
do
    echo "export $l"
done \
    < fortnite-matrix-bot.env )"

./fortnite-matrix-bot.py
