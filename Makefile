.PHONY: all up debug

all:

up:all
	sed -i 's/localhost:8080/hellodj.appspot.com/' static/test.html
	python ../appcfg.py --email=damn.su@gmail.com update .
	sed -i 's/hellodj.appspot.com/localhost:8080/' static/test.html

debug:
	cp static/*.js pack
