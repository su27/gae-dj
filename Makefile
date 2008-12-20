.PHONY: all up

all:
	sed -i 's/localhost:8080/hellodj.appspot.com/' static/gae-dj.js

up:all
	python ../appcfg.py --email=damn.su@gmail.com update .

debug:
	sed -i 's/hellodj.appspot.com/localhost:8080/' static/gae-dj.js
