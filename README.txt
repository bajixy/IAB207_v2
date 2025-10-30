IAB207 – Event Management System





1) Recommended folder locations (per OS)



The app just needs a normal writable folder. Avoid read-only/system paths or folders aggressively managed by cloud sync.



Windows (recommended)



	 Good: C:\\Users\\<you>\\a2\_groupX (your Home), C:\\Users\\<you>\\Desktop\\a2\_groupX, C:\\Users\\<you>\\Documents\\a2\_groupX



	 Avoid: C:\\Program Files\\…, C:\\Windows\\…, OneDrive Desktop/Documents (can be OK, but sometimes blocked/locked)



	macOS (recommended)



	Good: ~/a2\_groupX, ~/Projects/a2\_groupX, ~/Desktop/a2\_groupX



	 Avoid: /System, /Library, /Applications, iCloud Desktop/Documents (if “Optimize Mac Storage” may make files read-only)



Linux (recommended)



	 Good: ~/a2\_groupX, ~/Projects/a2\_groupX



	 Avoid: /usr, /opt (unless you know permissions), read-only mounts



2) What’s included



	website/\_data/app.db — seed/demo database shipped with the repo (read/write in-place).

	instance/ — local dev data (created on first run if needed), ignored by git.
	
	requirements.txt — pinned dependencies (Flask, Flask-Login, Flask-SQLAlchemy, Bootstrap-Flask, WTForms, etc.).

	main.py — app entry with create\_app() bootstrap.

	website/ — Flask package: models, routes, forms, templates, static assets.

	The app auto-selects a DB in this order:
	
	If DATABASE\_URL env var is set → use it.

	Else if website/\_data/app.db exists → use that (the packaged demo DB).

	Else fallback to instance/app.db (auto-created).





How to run the project from the ZIP

1) Unzip it

	Extract the ZIP so you get a folder like a2\_groupX/


	Inside you should see: main.py, a website/ folder, requirements.txt, etc.



2) Make sure Python 3.10+ is installed

	Windows: py --version


	macOS/Linux: python3 --version


If it’s missing, install from python.org.




3) Create \& activate a virtual environment

Windows (PowerShell)**

	cd a2\_groupX**

	py -m venv venv**

	.\\venv\\Scripts\\Activate.ps1**



Windows (CMD)

	cd a2\_groupX**

	py -m venv venv**

	venv\\Scripts\\activate**



macOS / Linux (Terminal)

	cd a2\_groupX**

	python3 -m venv venv**

	source venv/bin/activate**







4) Install dependencies

	pip install -r requirements.txt

5) Run the app


	flask --app main.py run

