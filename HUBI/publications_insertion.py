#!/usr/bin/env python
############################################################################
#
# Edgar Carrera
# ecarrera@cern.ch
#
# June, 2020
# This scriipt takes a cvs input file (the output of the
# publication_extraction.py script) with a list of DOI of publications
# that need to be inserted in the hubi publications and investigations
# platform and makes the best it can to fill out the different fields.
# The actual PDF files need to be uploaded manually
#
############################################################################

"""
   usage: %prog [options]
   -f, --file = FILE: file with DOI
"""
import os,sys
import string, re
import fileinput
import subprocess
import bibtexparser
import io
from selenium import webdriver
from selenium.webdriver.support.ui import Select
import getpass
from time import gmtime, localtime, strftime, sleep
from difflib import SequenceMatcher

#location of chromedriver
cromedriverloc = '/usr/bin/chromedriver'
#default download location for chrome
downdir = '/home/ecarrera/Downloads'
#user email and ID
userEmail = "ecarrera@usfq.edu.ec"
userID = "183"
indexPageURL = 'https://hubi.usfq.edu.ec/index.php'
mainHubiURL = 'https://hubi.usfq.edu.ec/mainpage.php'
inspireURL = 'https://inspirehep.net/'

###############################################################
class Pubobject:
    def __init__(self, path, weight):
        self.path=path
        self.weight=weight
###############################################################

############################################################################ OPTIONS
# Code taken from http://code.activestate.com/recipes/278844/
############################################################################
import optparse
USAGE = re.compile(r'(?s)\s*usage: (.*?)(\n[ \t]*\n|$)')
def nonzero(self): # will become the nonzero method of optparse.Values
    "True if options were given"
    for v in self.__dict__.itervalues():
        if v is not None: return True
    return False

optparse.Values.__nonzero__ = nonzero # dynamically fix optparse.Values

class ParsingError(Exception): pass

optionstring=""

def exit(msg=""):
    raise SystemExit(msg or optionstring.replace("%prog",sys.argv[0]))

def parse(docstring, arglist=None):
    global optionstring
    optionstring = docstring
    match = USAGE.search(optionstring)
    if not match: raise ParsingError("Cannot find the option string")
    optlines = match.group(1).splitlines()
    try:
        p = optparse.OptionParser(optlines[0])
        for line in optlines[1:]:
            opt, help=line.split(':')[:2]
            short,long=opt.split(',')[:2]
            if '=' in opt:
                action='store'
                long=long.split('=')[0]
            else:
                action='store_true'
            p.add_option(short.strip(),long.strip(),
                         action = action, help = help.strip())
    except (IndexError,ValueError):
        raise ParsingError("Cannot parse the option string correctly")
    return p.parse_args(arglist)

#######################################################
def get_dois_from_csv(thefile):
#######################################################

    #iterate over all doi's in the file
    linecount = 0
    doiList = []
    for line in thefile.readlines():
        #first line is the titles
        if (linecount>0):
            #get the doi of the publication to be uploaded
            #there is something weird with an extra comma in some cases
            #but I try to get rid of it if that is the case
            #It mayb break
            thedoi = str(line.split("|")[0])
            doiList.append(thedoi)
        linecount=linecount+1

    return doiList

#######################################################
def get_password():
#######################################################
     thePass = getpass.getpass()
     return thePass

#######################################################
def get_bibtex_info(idriver):
#######################################################
    idriver.find_element_by_xpath("//div[@class='__Literature__']").click()
    idriver.find_element_by_xpath("//div[@class='ant-row']").click()
#    idriver.find_element_by_xpath("//div[@class='ant-row ant-row-space-between actions ph2']").click()

    divs = idriver.find_elements_by_tag_name("div")
    buttons = idriver.find_elements_by_tag_name("button")

    

    print("----divs")
    for tag in divs:
        print (tag.get_attribute("class"))
    print("----buttons")
    for tag in buttons:
        print (tag.get_attribute("class"))
        
    
    idriver.find_element_by_xpath("//button[@class='ant-btn']").click()
    idriver.find_element_by_xpath("//span[@aria-label='download']").click()
    sleep(5)
    str_ls = "ls -1rt "+downdir
    mypipe = subprocess.Popen(str_ls,shell=True,stdout=subprocess.PIPE)
    thebib = mypipe.communicate()[0].split()[-1].decode("utf-8")
    print (thebib)
    #change the name
    bibtex_file = downdir+"/"+thebib

    #read the file and parse it with bibtexparser 
    with open(fbib) as bibtex_file:
        bibtex_str = bibtex_file.read()
    #get the list of dictionaries for bibtex entries
    bib_database = bibtexparser.loads(bibtex_str)
    #form the dictionary like the hubi dictionary
    for pub in bib_database.entries:
        print(pub)
        
    thepub = bib_database[0]
    print(thepub)

    return thepub

#######################################################
def get_publication_inspire_info(doi,idriver):
#######################################################
    print("******get_publication_inspire_info")
    idriver.get(inspireURL)
    success = True
    theinput = idriver.find_element_by_xpath("//input[@data-test-id='search-box-input']")
    theinput.clear()
    theinput.send_keys(doi)
    idriver.find_element_by_xpath("//button[@class='ant-btn ant-input-search-button ant-btn-primary ant-btn-lg']").click()
    sleep(5)
    thepa2s=idriver.find_elements_by_xpath("//div[@class='pa2']")
    #if there are more than one result, report to check manually
    if len(thepa2s)>1:
        print ("There are more than one result for doi "+doi+" in inspire.  This is odd, please check manually ...")
        success = False
        thepub = Pubobject(0,0)
    if len(thepa2s)==1:    
        #click on the publication
        idriver.find_element_by_xpath("//a[@data-test-id='literature-result-title-link']").click()
        thepub = get_bibtex_info(idriver)

    return thepub,success
#######################################################
def insert_publications_inhubi(dicOpt):
#######################################################

    #open crome for hubi
    driver = webdriver.Chrome(cromedriverloc)
    #open crome for inspire
    idriver = webdriver.Chrome(cromedriverloc)
    #sign in hubi
    driver.get(indexPageURL)
    userEl = driver.find_element_by_id('usuario')
    userEl.clear()
    userEl.send_keys(userEmail)
    passEl = driver.find_element_by_id('password')
    passEl.clear()
    thePass = get_password()
    passEl.send_keys(thePass)
    driver.find_element_by_class_name("submit").click()
    print (driver.current_url)
    assert driver.current_url == mainHubiURL
    #open file with doi
    thefile = open(dicOpt['file'],"r")
    #get the list of dois from csv
    doiList = get_dois_from_csv(thefile)
    #collect the dois that could not be processed
    notdoiList = []
    tempcount = 1
    #loop over all dois found
    for doi in doiList:
        thepub,status = get_publication_inspire_info(doi,idriver)
        if status:
            print (status)
            #fill_out_hubi_pub(thepub,driver)
            #fill_out_hubi_entregable(thepub,driver)
        else:
            notdoiList.append(doi)
        tempcount+=1
        
        if tempcount>2:
            driver.quit()
            exit(0)
        
    print (doiList)
    
#######################################################
def get_default_options(option):
#######################################################
    dicOpt = {}

    #the file
    if not option.file:
        print ("no filename given")
    else:
        dicOpt['file']= str(option.file)

    return dicOpt


#######################################################
if __name__ =='__main__':
#######################################################

    #import optionparser
    option,args = parse(__doc__)
    if not args and not option:
        print ("You need a cvs input file")
        exit(0)
        
    #set default options
    dicOpt = get_default_options(option)

    #run the insertion
    insert_publications_inhubi(dicOpt)
