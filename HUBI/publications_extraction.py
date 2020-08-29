#!/usr/bin/env python
############################################################################
#
# Edgar Carrera
# ecarrera@cern.ch
#
# August 8, 2017
# Script to extract a publication list from hep inspire,
# compare it to hubi (usfq) and generate a list
# of already uploaded publications and publication pending upload
#
# May 31, 2020
# Inspire already switched to a new site
# Now the robot needs work to make inspire list automatic
# For now, then, you can make it run after saving a Bibtex summary (button
# cite all) with the name like pub_bibtex_2020.txt.  Use the following
# sintax in the inspire literatur search window:
# a E.Carrera.Jarrin.1 and tc p and date 2019
#
# Jun 9, 2020
# Year refers to year in "date year" in the inspire search string
# I removed the option to additional strings as I never use it.
############################################################################

"""
   usage: %prog [options]
   -y, --jyear = JYEAR: journal year of publication

"""

import os,sys
import string, re
import fileinput
import subprocess
import bibtexparser
import io
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
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

#needed urls
indexPageURL = 'https://evaluaciones.usfq.edu.ec/hubi/index.php'
mainPageURL = 'https://evaluaciones.usfq.edu.ec/hubi/mainpage.php'
mainPHPURL = 'https://evaluaciones.usfq.edu.ec/hubi/mainpage_apps.php'
mainPubsURL = 'https://evaluaciones.usfq.edu.ec/hubi/publicaciones/index.php'

pubsURL = 'https://evaluaciones.usfq.edu.ec/hubi/publicaciones/admin/autores_publicaciones.php?autor_id='+userID
thePubURL = 'https://evaluaciones.usfq.edu.ec/hubi/publicaciones/admin/publicaciones_datos.php?publicacion_id='
basicInspireURL = 'https://inspirehep.net/literature?sort=mostrecent&size=25&page=1&q=a%20E.Carrera.Jarrin.1%20and%20tc%20p%20and%20date%20'
#interesting fields list

#these need access for <select>
fieldName_selectValueAndTextList = [
'publicacion_tipo', #value and text
'publicacion_idioma', #value and text
'publicacion_investigacion_tipo',#value and text
'publicacion_area_conocimiento', #value and text
]

#these need access for <input>, just an webelement
fieldName_inputValueList = [
'publicacion_anio',#value
'publicacion_url',#value
'articulo_general_tipo',#value
'articulo_general_formato',#value
'articulo_revista_scopus',#value
'articulo_revista_issn',#value
'articulo_revista_cod_scopus',#value
'articulo_revista_pais',#value
]
fieldName_inputTextList = [
'publicacion_titulo',#text
'articulo_revista_nombre',#text
'articulo_revista_otra',#text
'articulo_revista_volumen',#text
'articulo_revista_numero',#text
'articulo_rango_paginas',#text
'articulo_doi',#text
]


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
def flatten(dictionary):
#######################################################    
    for key, value in dictionary.items():
        if isinstance(value, dict):
            # recurse
            for res in flatten(value):
                yield res
        else:
            yield key, value


            
#######################################################    
def get_key_from_dict_byvalue(dictionary, value_to_find):
#######################################################        
    for key, value in flatten(dictionary):
        if value == value_to_find:
            return key

#######################################################
def compare_publication_titles(dictOne,dictTwo):         
#######################################################    
    #this is to compare titles of publications in
    #inspire with the titles in the hubi
    ratios = []
    #print "++++++++++++++++++++++++++++++++++++++++++++++++"
    titleOne = dictOne['title'].replace('\n',' ')
    #print "The ratio between "+titleOne+"\n"
    for pubTwo in dictTwo:
        titleTwo = dictTwo[pubTwo]['publicacion_titulo'].replace('\n',' ')
        theratio = SequenceMatcher(None, titleOne, titleTwo).ratio()
        #print "\t *****AND**** "+titleTwo+" is ^^^"+str(theratio)
        if (theratio>0.9):
            ratios.append(theratio)
            
    return ratios
                
#######################################################
def get_the_toupload_dictionary(inspDict,hubiDict):
#######################################################
    #make a comparison of inspire and hubi
    #dictionaries and generate a dictionary
    #with those publications that are in inspire
    #but not in the hubi
    toUploadDict = {}
    for thekey in inspDict:
        isHubiDoi = get_key_from_dict_byvalue(hubiDict,thekey)
        if not isHubiDoi:
            print ("Doi "+thekey+"\t was not found.  Searching now by title, just in case ... ")
            titleRatios = compare_publication_titles(inspDict[thekey],hubiDict)
            if (not len(titleRatios)==1):
                toUploadDict[thekey]=inspDict[thekey]
                print ("....sorry, the title was NOT FOUND.")
            else:
                toUploadDict[thekey]=inspDict[thekey]
                print ("A very similar Title "+inspDict[thekey]['title']+" WAS FOUND!!!  This is weird please check for this DOI")
        else:
            print ("Doi "+thekey+" WAS FOUND!!!")

    return toUploadDict
                



#######################################################
def print_csv_file(theDict,cvs_file_title):
#######################################################
#     f = open(cvs_file_title,'w')
     theTitle = str(cvs_file_title)
     f = io.open(theTitle,'w',encoding='utf8')
     countk = 0
     theFirstLine = 'Pub ID'
     for k in theDict:
          theLine = str(k)
          countj = 0
          jsize = len(theDict[k])
          for j in theDict[k]:
               if (countk==0):
                    if (countj != (jsize-1)):
                         theFirstLine = theFirstLine+"|"+j
                         theLine = theLine+"|"+theDict[k][j].replace('\n',' ')
                    else:
                         theFirstLine = theFirstLine+"|"+j+"\n"
                         theLine = theLine+"|"+theDict[k][j].replace('\n',' ')+"\n"
               else:
                    if (countj != (jsize-1)):
                         theLine = theLine+"|"+theDict[k][j].replace('\n',' ')
                    else:
                         theLine = theLine+"|"+theDict[k][j].replace('\n',' ')+"\n"
               countj = countj + 1
          _theFirstLine = str(theFirstLine)
          _theLine = str(theLine)
          if (countk==0):          
               f.write(_theFirstLine)
               f.write(_theLine)
          else:
               f.write(_theLine)

          countk = countk + 1

     f.close()
     print ("\nMake sure to select | as your delimiter\n")


#######################################################
def get_password():
#######################################################
     thePass = getpass.getpass()
     return thePass


#######################################################
def get_hubi_pubs_ids(theDriver):
#######################################################
     theSource = theDriver.page_source
     idList = []
     for k in theSource.split():
          if (k.find('publicacion_id')!= -1):
               idList.append(str(k.split("=")[3].split('\'')[0]))
     return idList

#######################################################
def scrape_the_publication(theDriver,iPubDict):
#######################################################
     #get fields with values and text (<select>)
     for j in fieldName_selectValueAndTextList:
          #check if the element exists
          isPresent = theDriver.find_elements_by_name(j)
          field_value = j+"_value"
          field_text = j+"_text"
          if (isPresent):
               select = Select(theDriver.find_element_by_name(j))
               theEle = select.first_selected_option
               theValue = theEle.get_attribute("value")
               theText = theEle.text
               #fill the dictionary
               iPubDict[field_value] = theValue
               iPubDict[field_text] = theText
          else:
               iPubDict[field_value] = 'N/A'
               iPubDict[field_text] = 'N/A'
               
     #get fields with only values (<input>)
     for j in fieldName_inputValueList:
          isPresent = theDriver.find_elements_by_name(j)
          if (isPresent):
               theEle = theDriver.find_element_by_name(j)
               theValue = theEle.get_attribute("value")
               #fill the dictionary
               iPubDict[j] = theValue
          else:
               iPubDict[j] = 'N/A'
               
     #get fields with only text (<input>)
     for j in fieldName_inputTextList:
          isPresent = theDriver.find_elements_by_name(j)
          if (isPresent):
               theEle = theDriver.find_element_by_name(j)
               theText = theEle.text
               #fill the dictionary
               iPubDict[j] = theText
          else:
               iPubDict[j] = 'N/A'
               
          
#######################################################
def scrape_the_hubi(theDriver):
#######################################################
     #create the dictionary for the publications
     #['id':[fields]]
     allPubsDict = {}
     #get the publications ids
     thePIds = get_hubi_pubs_ids(theDriver)
     #scrape the publications
     #count = 0;
     for k in thePIds:
          #if count>5: break
          thePub = thePubURL+k
          theDriver.get(thePub)
          print (theDriver.current_url)
          allPubsDict[k] = {}
          scrape_the_publication(theDriver,allPubsDict[k])
          #count = count + 1
     return allPubsDict


#######################################################
def get_hubi_publication_dictionary():
#######################################################

     #create a phantom webdriver
     #driver = webdriver.PhantomJS()
     driver = webdriver.Chrome(cromedriverloc)
#     driver.set_window_size(1120, 550)

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
     assert driver.current_url == mainPageURL
     
     #make sure you get access to the publications list
     driver.get(mainPHPURL)
     print (driver.current_url)
     driver.get(mainPubsURL)
     print (driver.current_url)
     driver.get(pubsURL)
     print (driver.current_url)
     
     #get the hubi publications dictionary
     pubsDict = scrape_the_hubi(driver)
     #driver.save_screenshot('screen.png')
     driver.quit()
     return pubsDict


#######################################################
def get_inspire_publication_dictionary(dicOpt):
#######################################################

    theyear = dicOpt['jyear']
    fString = basicInspireURL+str(theyear)
    print ("Search string: "+fString)
    driver = webdriver.Chrome(cromedriverloc)
    driver.get(fString)
    sleep(10)
    citeEl = driver.find_element_by_xpath("//button[@class='ant-btn ant-dropdown-trigger']")
    citeEl.click()
    thehover = ActionChains(driver).move_to_element(citeEl)
    thehover.perform()
    driver.save_screenshot("screenshot.png")
    thebib = driver.find_element_by_xpath("//li[contains(text(),'BibTeX')]").click()
    sleep(10)
    #this works but then one needs to grab the file from the
    #Download directory
    str_ls = "ls -1rt "+downdir
    mypipe = subprocess.Popen(str_ls,shell=True,stdout=subprocess.PIPE)
    thebib = mypipe.communicate()[0].split()[-1].decode("utf-8")
    print (thebib)
    #change the name
    fbib = "pub_bibtex_"+theyear+".txt"
    os.system("mv "+downdir+"/"+thebib+" "+fbib)

    #read the file and parse it with bibtexparser 
    with open(fbib) as bibtex_file:
        bibtex_str = bibtex_file.read()
    #get the list of dictionaries for bibtex entries
    bib_database = bibtexparser.loads(bibtex_str)
    #form the dictionary like the hubi dictionary
    allPubsDict = {}
    for pub in bib_database.entries:
        theID = pub['doi']
        allPubsDict[theID] = pub

    #print allPubsDict
    driver.quit()
    return allPubsDict
        

#######################################################
def get_default_options(option):
#######################################################
    dicOpt = {}

    #for the publication year
    if not option.jyear:
        dicOpt['jyear']= ""
    else:
        dicOpt['jyear']= str(option.jyear)

    return dicOpt

#######################################################
if __name__ =='__main__':
#######################################################

    #import optionparser
    option,args = parse(__doc__)
    if not args and not option:
        print ("\nWARNING: your are executing the search without any input options ...")

    #set default options
    dicOpt = get_default_options(option)

    #print configuration
    print ("-----------")
    print ("This is the configuration you are using:")
    for k in dicOpt:
        print (str(k)+"\t = "+str(dicOpt[k]))
    print ("-----------")

    #form csv filenames
    if (dicOpt['jyear']!=""):
        cvs_insp_title = 'inspire_publications_'+dicOpt['jyear']+".csv"
        cvs_up_title = 'toupload_publications_'+dicOpt['jyear']+".csv"
    else:
        cvs_insp_title = 'inspire_publications.csv'
        cvs_up_title = 'toupload_publications.csv'

    #get the cvs files
    print ("------- Getting the most current USFQ HUBI publications ...")
    hubiDict = get_hubi_publication_dictionary()
    print_csv_file(hubiDict, "hubi_publications.csv")
    
    print ("------- Getting the requested inspire publications ...")
    inspDict = get_inspire_publication_dictionary(dicOpt)
    print_csv_file(inspDict,cvs_insp_title)
    
    print ("------- Comparing databases and printing results ...")
    upDict = get_the_toupload_dictionary(inspDict,hubiDict)
    print_csv_file(upDict, cvs_up_title)
