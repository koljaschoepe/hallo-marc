PY := .venv/bin/python

.PHONY: help setup discover probe hallo face weather transit notify run

help:
	@echo "make setup              venv + Abhaengigkeiten"
	@echo "make discover           SmallTV im WLAN finden"
	@echo "make probe              Status des Geraets (IP aus .env)"
	@echo "make hallo              Begruessung neu bauen und aufspielen"
	@echo "make face MOOD=happy    Gesicht (neutral happy listening thinking speaking sad)"
	@echo "make weather            Wetterkarte anzeigen"
	@echo "make transit            Abfahrtstafel anzeigen"
	@echo "make notify TEXT='...'  Hinweis anzeigen"
	@echo "make run                Companion-Daemon (Tafel + Wetter + Hinweise)"

setup:
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt
	@test -f .env || cp .env.example .env
	@echo "Fertig. Jetzt: make discover, dann IP in .env eintragen."

discover:
	$(PY) -m smalltv.discover

probe:
	@$(PY) -c "from smalltv.client import SmallTVClient; from smalltv.config import Config; \
import json; s=SmallTVClient(Config.from_env().ip).status(); print(json.dumps(s.raw, indent=2))"

hallo:
	$(PY) -m smalltv.greeting deploy

MOOD ?= neutral
face:
	@$(PY) -c "import pathlib,sys; sys.exit(0 if pathlib.Path('.face_deployed').exists() else 1)" \
		|| ($(PY) -m smalltv.face deploy && touch .face_deployed)
	$(PY) -m smalltv.face show $(MOOD)

weather:
	@$(PY) -c "from smalltv import weather; from smalltv.client import SmallTVClient; \
from smalltv.config import Config; c=Config.from_env(); \
SmallTVClient(c.ip).push_image(weather.render_card('out/weather.gif'))"

transit:
	$(PY) -m smalltv.transit show

notify:
	$(PY) -m smalltv.notify "$(TEXT)"

run:
	$(PY) -m smalltv.companion
