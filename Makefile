PYTHON ?= python

.PHONY: setup build build-ra build-lecturer run-ra run-lecturer dry-run-ra dry-run-lecturer clean

setup:
	$(PYTHON) -m pip install -r requirements.txt pyinstaller

build: build-ra build-lecturer

build-ra:
	cd ra_job_scanner && $(PYTHON) -m PyInstaller --onefile --console --name "RA_Job_Scanner" --clean scan.py
	cp ra_job_scanner/dist/RA_Job_Scanner.exe ra_job_scanner/RA_Job_Scanner.exe
	rm -rf ra_job_scanner/build ra_job_scanner/dist ra_job_scanner/RA_Job_Scanner.spec

build-lecturer:
	cd lecturer_scanner && $(PYTHON) -m PyInstaller --onefile --console --name "Lecturer_Job_Scanner" --clean scan.py
	cp lecturer_scanner/dist/Lecturer_Job_Scanner.exe lecturer_scanner/Lecturer_Job_Scanner.exe
	rm -rf lecturer_scanner/build lecturer_scanner/dist lecturer_scanner/Lecturer_Job_Scanner.spec

run-ra:
	cd ra_job_scanner && $(PYTHON) scan.py

run-lecturer:
	cd lecturer_scanner && $(PYTHON) scan.py

dry-run-ra:
	cd ra_job_scanner && $(PYTHON) scan.py --dry-run

dry-run-lecturer:
	cd lecturer_scanner && $(PYTHON) scan.py --dry-run

clean:
	rm -rf ra_job_scanner/build ra_job_scanner/dist ra_job_scanner/*.spec
	rm -rf lecturer_scanner/build lecturer_scanner/dist lecturer_scanner/*.spec
