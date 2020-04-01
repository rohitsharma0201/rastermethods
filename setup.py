'''
====================================================================================
setup.py: Automated installation of dependencies required for Python raster function
====================================================================================

Installation
------------

To execute **setup.py** within the package directory run:
  $ python setup.py
'''

import sys
import logging
from os import path, makedirs
from subprocess import call
from time import sleep


'''
    ErrorLevel on exit:
        0  :    Installation successful.
        1  :    PIP installation unsuccessful.
        2  :    File cannot be downloaded.
        4  :    VC++ Compiler for Python installation failed.
        5  :    Requirements.txt file not found.
        6  :    Python package installation failed.
        99 :    ArcGIS 10.3.1 or above not found.
'''

def log(s):
    print(">>> {0}".format(s))


def die(errorLog, errorCode):
    print("\n\n")
    logging.error(errorLog)
    print("\n")
    sleep(2)
    exit(errorCode)
    

def downloadFile(url, filePath):
    try:
        log("Downloading: {0} to {1}".format(url, filePath))

        try:
            from urllib2 import urlopen
        except: 
            from urllib.request import urlopen

        d = path.dirname(filePath)
        if not path.exists(d):
            makedirs(d)

        with open(filePath, 'wb') as f:
            f.write(urlopen(url).read())
    except:
        die("Unable to download URL", 2)


def locateFile(url, filePath):
    if not path.isfile(filePath):
        downloadFile(url, filePath)
    log("Located: {0}".format(filePath))


def main():
    pipURL = "http://bootstrap.pypa.io/get-pip.py"
    vcURL = "http://download.microsoft.com/download/7/9/6/796EF2E4-801B-4FC4-AB28-B59FBF6D907B/VCForPython27.msi"

    pipExePath = path.join(path.dirname(sys.executable), r"Scripts\pip.exe")
    setupHome = path.join(path.abspath(path.dirname(__file__)), "scripts")
    distHome = path.join(path.abspath(path.dirname(__file__)), "dist")

    try:
        log("Installing PIP")
        pipPyPath = path.join(setupHome, "get-pip.py")
        locateFile(pipURL, pipPyPath)
        call([sys.executable, pipPyPath])

        if path.isfile(pipExePath):
            log("PIP installed successfully")
        else:
            raise Exception("PIP failed")

        call([pipExePath, "install", "--upgrade", "--no-index", "--find-links={0}".format(distHome), "pip"])
        call([pipExePath, "install", "--upgrade", "--no-index", "--find-links={0}".format(distHome), "wheel"])
    except:
        die("PIP installation failed!", 1)
    
    try:           
        if sys.version_info[0] == 2:
            log("Installing Microsoft Visual C++ Compiler")
            vcSetupPath = path.join(distHome, "VCForPython27.msi")
            locateFile(vcURL, vcSetupPath)
            c = ["msiexec", "/i", vcSetupPath, "/qb-"]
            log("Executing: {0}".format(" ".join(c)))
            call(c)
            log("C++ Compiler for Python installed successfully")
    except:
        die("VC++ Compiler for Python installation failed!.", 4)

    try:
        log("Installing Python dependencies")
        reqFilePath = path.join(setupHome, "requirements.txt")
        if not path.isfile(reqFilePath):
            die("Dependency listing file not found: {0}".format(reqFilePath), 5)

        c = [pipExePath, "install", "--upgrade", "--no-index", "--find-links={0}".format(distHome), "-r", reqFilePath]
        log("Executing: {0}".format(" ".join(c)))
        call(c)
    except:
        die("Dependency installation failed!", 6)
    
    try:
        arcpy = __import__('arcpy')
        info = arcpy.GetInstallInfo()

        bVersionOK = True
        
        minArcGISVersion = '10.3.1'
        if info['Version'].split(".")[0] == 10 and (tuple(map(int, (info['Version'].split(".")))) < tuple(map(int, (minArcGISVersion.split("."))))):
           bVersionOK = False

        minProVersion = '1.0'
        if info['Version'].split(".")[0] == 1 and (tuple(map(int, (info['Version'].split(".")))) < tuple(map(int, (minProVersion.split("."))))):
           bVersionOK = False

        if not bVersionOK:
           raise Exception("No ArcGIS")
               
        print("\n\n")
        if info['Version'][0] == 10:
            log("Python extensions for raster functions in ArcGIS {} {} build {} successfully installed.".format(
                info['ProductName'], info['Version'], info['BuildNumber']))
        else:
            log("Python extensions for raster functions in {} {} build {} successfully installed.".format(
                info['ProductName'], info['Version'], info['BuildNumber']))
    except:
        logging.warn("Unable to find ArcGIS 10.3.1/ArcGIS Pro 1.0 or above.")

    log("Done.")
    sleep(2)
    exit(0)


if __name__ == '__main__':
    main()


# Uninstall using: pip uninstall --yes -r requirements.txt