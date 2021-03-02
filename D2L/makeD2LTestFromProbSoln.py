#!/usr/bin/env python
############################################################################
#
# Edgar Carrera
# ecarrera@usfq.edu.ec
#
# This script is a robot to create D2L tests at USFQ.
#
# Oct 19, 2020
# Updated the parser to work with random problem generation from Latex
# package probsoln.  We basically need:
# -The PDF file in a one problem per page format: e.g, ExamenMaestriaA.pdf
#  This file should have the problems labels at the end, e.g., mecanica::05,
#  which corresponds to its associated tex files from where we extract the
#  answers
# -All the tex files like mecanica.tex, ondas.tex, etc., where the solutions
# will be extracted
# To execute do something like
# $> python makeD@LTestFromProbSoln.py -t EM -f ExamenMaestriaParteA.pdf
#
# It needs to have ParteA or ParteB in the name.

# Oct 15, 2020
# After D2L upgrade at USFQ, many things got broken. We fixed this and tried
# to avoid using ids that are dynamic (we are still lazy with a few things)
#
#
# May 12, 2020
# - It needs python 3
# - Currently it only creates EM tests based on images and answers extracted
#  from a one-problem-per-page PDF file and its associated tex file (which
#  needs to have the same basename).  Both
#  have to be in the directory where you run the script
# - Most of the modifiable stuff is in the header.
# - Use python makeD2LTest.py -h to print usage
# - Ex. of usage: python makeD2LTest.py -t EM -f myfile.pdf
############################################################################
"""
   usage: %prog [options]
   -t, --type = TYPE: Type of D2L exam (currently only EM)
   -f, --file = FILE: Input file (for now only PDF)

"""

import os,sys
import string, re
import fileinput
import subprocess
import io
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
#from selenium.webdriver.support.ui import Select
#from selenium.webdriver.common.action_chains import ActionChains
import getpass
from time import gmtime, localtime, strftime, sleep
import datetime
from difflib import SequenceMatcher
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#################################################################
#These are global variables that can be changed according to needs
cromedriverloc = '/usr/bin/chromedriver'
userEmail = "ecarrera@usfq.edu.ec"
#d2lcourseID = "137997" #fermi2020
#d2lcourseID = "141761" #qm
d2lcourseID = "156664" #hep
#d2lcourseID = "120409" #dummy
theppi = 300 #density for images
stringA = "prueba1"
stringB = "ParteB"
labelsA = ['particles::']
           
labelsB = ['moderna::',
           'metodos::',
           'compleja::']
##################################################################
#Don't change this unless there are changes in d2l framework
d2lloginpage = "https://miusfv.usfq.edu.ec/"
d2lhomepage = "https://miusfv.usfq.edu.ec/d2l/home"
d2lcoursenewtestpage = "https://miusfv.usfq.edu.ec/d2l/lms/quizzing/admin/modify/quiz_newedit_properties.d2l?ou="+d2lcourseID

###########################################################################
# OPTIONS (argument handler)
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
def get_password():
#######################################################
     thePass = getpass.getpass()
     return thePass

#######################################################
def reset_EMquestion_driver(driver):
#######################################################
    #Need to make the appropiate container active, switch to needed iframe
    #and activate children containers (we add some waiting time, it is needed.  Improve it)
    driver.switch_to.default_content()
    driver.implicitly_wait(25)
    #for item in driver.find_elements_by_tag_name("iframe"):
    #     print (item.get_attribute('title'))
    #exit(1)
    #driver.switch_to.frame(driver.find_elements_by_tag_name("iframe")[1])
    driver.switch_to.frame(driver.find_element_by_xpath("//iframe[@title='Question Editor']"))
    #driver.save_screenshot("screenshot6.png")
    return driver


#######################################################
def reset_EM_uploadDialog_driver(driver):
#######################################################
     #This dialog might be the same for all kind of questions
     #that is why I write it separately
     #When it opens, this iframe is unique
     driver.switch_to.default_content()
     ifEl = driver.find_element_by_xpath("//iframe[@class='d2l-dialog-frame']")
     driver.switch_to.frame(ifEl)

     return driver

#######################################################
def add_EM_answers(driver,nadd):
#######################################################
     #sometimes this page does not load rapidly
     sleep(3)
     for i in range(1,nadd+1):
         driver.find_element_by_xpath("//d2l-button-subtle[@id='add-option']").click()

     return driver


#######################################################
def input_EM5_pdfanswers(driver):
#######################################################
     #reset question page (for html scope reasons)
     driver = reset_EMquestion_driver(driver)
     #hardcoded limits
     #D2l presents 4 default answers, we adding one more.
     extraans = 1
     defaultanswers = 4
     #add extra answer
     driver=add_EM_answers(driver,extraans)
     #Now fill out the answers
     possible_answers = ["A","B","C","D","E"]
     for i in range(0,defaultanswers):
          #print ("Building answer",i)
          mylabel = "qed-option-answer_"+str(i+1)
          #print (mylabel)
          box=driver.find_element_by_xpath("//div[@class='d2l-richtext-editor-container mce-content-body' and @id ='"+mylabel+"']")
          sleep(1)
          box.click()
          box.clear()
          box.send_keys(possible_answers[i])

     #fill out the last one
     sleep(5)
     theboxes = driver.find_elements_by_xpath("//div[@class='d2l-richtext-editor-container mce-content-body']")
     lastbox = theboxes[-1]
     lastbox.click()
     lastbox.clear()
     lastbox.send_keys(possible_answers[-1])

     return driver

######################################################
def select_EM5_solution(driver,solution):
######################################################
     driver = reset_EMquestion_driver(driver)
     #get the five choices
     tags = driver.find_elements_by_xpath("//input[@type='checkbox' and contains(@name,'question.response')]")
     #click on the right one
     #solution has to be from 0 to 4
     tags[solution].click()

     return driver
######################################################
def add_EM5_image(driver,imgname):
#######################################################
     driver = reset_EMquestion_driver(driver)
     #click on the empty paragraph box
     driver.find_element_by_xpath("//div[@class='d2l-richtext-editor-container mce-content-body']").click()
     #click on the camera icon
     driver.find_element_by_xpath("//div[@aria-label='Agregar imagen']/button[contains(@id,'mceu')]").click()

     #switch to upload dialog frame
     reset_EM_uploadDialog_driver(driver)
     #clcik on Mi PC option
     driver.find_element_by_xpath("//a[@title='Mi PC']").send_keys("\n")
     #execute de button "Cargar"
     driver.find_element_by_xpath("//button[contains(@id,'d2l_1_3')]").send_keys("\n")
     #this introduces an input line (otherwise it is not visible)
     #to submit the file.  Give the file
     driver.find_element_by_xpath("//input[@class='d2l-fileinput-input']").send_keys(os.getcwd()+"/"+imgname)
     sleep(4)
     #click on "Agregar"
     driver.find_element_by_xpath("//div[@class='d2l-dialog-buttons']/button[1]").send_keys("\n")

     #onunload goes to d2l_body so we scope out
     driver.switch_to.default_content()
     #Fill out the "Proporcionar texto alternativo" with the
     #name of the file without extension
     driver.find_element_by_xpath("//input[contains(@id,'d2l_cntl') and @type='text']").send_keys(imgname.split(".")[0])
     sleep(3)
     #click on Aceptar
     driver.find_element_by_xpath("//table[@class='d2l-dialog-buttons']//button[@class='d2l-button']").send_keys("\n")
     sleep(2)

     return driver

#######################################################
def click_buttons_agregar_y_nueva_pregunta(driver):
#######################################################
     #This click is the same for any type of question
     #Switch to the frame where the magic happens
     #Look for similar (in python) as
     #https://www.guru99.com/handling-iframes-selenium.html
     #need to switch to the right frame
     #driver.switch_to.default_content()
     driver = reset_EMquestion_driver(driver)
     #driver.switch_to.parent_frame()
     #driver.find_element_by_xpath("//body[@id='d2l_body']")
     #driver.switch_to.frame(driver.find_elements_by_tag_name("iframe")[1])
     sleep(3)
     #click on 'Agregar'
     driver.find_element_by_xpath("//d2l-dropdown-button[@id='qed-quiz-builder-add-button']").click()
     sleep(3)
     #click on 'Nueva Pregunta'
     driver.find_element_by_xpath("//d2l-menu-item[contains(@text,'Nueva pregunta')]").click()
     return driver

#######################################################
def save_EM5_pdfquestion(driver):
#######################################################
     driver = reset_EMquestion_driver(driver)
     #click on Guardar
     sleep(3)
     driver.find_element_by_xpath("//button[@name='Submit']").send_keys("\n")
     #driver.save_screenshot("screenshot1.png")


     return driver


#######################################################
def create_new_EM5_pdfquestion(driver,solution,imgname):
#######################################################
     #print (driver.current_url)
     #click on crear nuevo
     sleep(2)
     driver = click_buttons_agregar_y_nueva_pregunta(driver)
     #click on "Pregunta de eleccion multiple" (EM)
     #for item in driver.find_elements_by_tag_name("d2l-menu-item"):
     #    print (item.get_attribute('text'))
     EMEl=driver.find_element_by_xpath("//d2l-menu-item[contains(@text,'Elección múltiple')]")
     print("We have chosen type: "+str(EMEl.get_attribute('text')))
     sleep(2)
     EMEl.click()
     
     #Now add answer options
     driver = input_EM5_pdfanswers(driver)
     #input the correct answer
     driver = select_EM5_solution(driver,solution)
     #add the image of the problem
     sleep(2)
     driver = add_EM5_image(driver,imgname)
     sleep(2)
     driver = save_EM5_pdfquestion(driver)
     sleep(2)
     #print (driver.current_url)

     return driver

#######################################################
def sign_in_d2l(driver):
#######################################################
     driver.get(d2lloginpage)
     userEl = driver.find_element_by_id('userNameInput')
     userEl.clear()
     userEl.send_keys(userEmail)
     driver.find_element_by_id("nextButton").click()
     passEl = driver.find_element_by_id('passwordInput')
     passEl.clear()
     #get the password by typing into the ommand line prompt
     thePass = get_password()
     passEl.send_keys(thePass)
     driver.find_element_by_id("submitButton").click()
     print (driver.current_url)
     #make sure we are in D2L
     assert driver.current_url == d2lhomepage

     return driver

#######################################################
def cat_tex_files(baseimgname):
#######################################################
    print ("Concatenating tex files ...")
    os.system("rm -f "+baseimgname+".tex")
    #use awk to concatenate due to new line after each
    #file issue
    cat_str = "awk \'{print}\' "

    #find out which type of exam it is A or B
    if stringA in baseimgname:
        for label in labelsA:
            cat_str = cat_str+label.split("::")[0]+".tex "

    if stringB in baseimgname:
        for label in labelsB:
            cat_str = cat_str+label.split("::")[0]+".tex "

    cat_str = cat_str+" > "+baseimgname+".tex"
    os.system(cat_str)
    return

#######################################################
def parse_texfile(baseimgname):
#######################################################
     print ("Parsing tex file "+baseimgname)
     #cat all the tex base files into just one tex file
     cat_tex_files(baseimgname)
     #decide what type of label files to use, A or B
     thelabel = ''
     if stringA in baseimgname:
         thelabels = labelsA
     if stringB in baseimgname:
         thelabels = labelsB
     #parse the txt file to get the list of labels needed
     txtfile = open(baseimgname+".txt")
     examlabels = []
     for iline in txtfile.readlines():
         if any(label in iline for label in thelabels ):
             examlabels.append(iline.rstrip().lstrip().split()[0])
     print ("\n Used problems are:")        
     print (examlabels)

     #now go through the merged tex file looking for the answers
     #stored in examlabels
     probIdx = 0
     solIdx = -1 #so it starts at 0
     solutions = {}
     withinQ = False
     texfile =open(baseimgname+".tex")
     for line in texfile.readlines():
         for label in examlabels:
             if label in line:
                 withinQ = True
                 probIdx =examlabels.index(label)+1
                 solIdx=-1
         if ("\\choice" in line and withinQ):
             solIdx +=1
         if ("\\CorrectChoice" in line and withinQ):
             solIdx +=1
             solutions[probIdx] = solIdx
         if ("\\end{defproblem}" in line  and withinQ):
             withinQ = False
     #sort dictionary by key
     sortedsol = {k:solutions[k] for k in sorted(solutions)}

     print ("Solutions: ")
     print (solutions)
     print ("Sorted solutions")
     print (sortedsol)
     
     return sortedsol

#######################################################
def process_pdffile(pdffile):
#######################################################
     print("Processing pdf file....")
     pdfDict = {}
     #make images out of pdf file
     baseimgname = pdffile.split(".")[0]
     os.system("rm -f "+baseimgname+"_*.png")
     str_conv = "convert -density "+str(theppi)+" -trim "+ pdffile+" -quality 100 -scene 1 "+baseimgname+"_%02d.png"
     os.system(str_conv)
     #convert pdf to text file
     os.system("rm -f "+baseimgname+".txt")
     str_txt = "pdftotext "+pdffile
     os.system(str_txt)
     #parse associated tex file for correct answers
     solDict = parse_texfile(baseimgname)
     probkeys = list(solDict.keys())
     print (probkeys)
     #make a dictionary image:solution
     str_ls = "ls -1 "+baseimgname+"_*.png"
     mypipe = subprocess.Popen(str_ls,shell=True,stdout=subprocess.PIPE)
     ipipe = mypipe.communicate()[0].split()
     probIdx = 0
     for prob in probkeys:
         imgfile = ipipe[probIdx].decode('ascii')
         assert (int(imgfile.split("_")[-1].split(".")[0])== prob)
         print ("Problem "+str(prob)+" --> "+imgfile)
         pdfDict[imgfile]=solDict[prob]
         probIdx+=1

     #Make a manifest for logging purposes
     os.system("rm -f manifest.txt")
     manif = open("manifest.txt","a")
     for img,sol in pdfDict.items():
         print (img+" Solution: "+str(sol)+"\n")
         manif.write(img+" Solution: "+str(sol)+"\n")

     return pdfDict, baseimgname

#######################################################
def create_d2l_EM5_pdftest(pdffile):
#######################################################

     #first deal with the pdffile
     #create a dictionary [image:solution]
     pdfDict, newquizname  = process_pdffile(pdffile)
     #exit(0)
     #create a selenium driver
     driver = webdriver.Chrome(cromedriverloc)
     driver.set_window_size(1920, 1000)
     print (driver.get_window_size())

     #sign in d2l
     driver = sign_in_d2l(driver)

     #access the new quiz page in the current course
     #I could have clicked in the button, but I was lazy.
     #As long as the url does not change, it will not break
     #but can be improved
     driver.get(d2lcoursenewtestpage)
          #fillout the name of the quiz
     #Select by xpath https://www.guru99.com/xpath-selenium.html
     #quizNameEl = driver.find_element_by_xpath("//input[@class='d2l-edit d2l-edit-legacy']")
     quizNameEl = driver.find_element_by_xpath("//input[@class='d2l-edit d2l-edit-legacy rs_skip']")
     quizNameEl.clear()
     quizNameEl.send_keys(newquizname)

     #Click on agregar preguntas, the stupid thing is not clickable
     #so the trick is to give it an enter ("\n") key
     qEl = driver.find_element_by_xpath("//button[@class='d2l-button' and contains(text(),'Agregar o editar preguntas')]")
     qEl.send_keys("\n")
     
     #now we have to loop in order to add multiple elective questions
     #solution has to be from 0 to 4
     probIdx = 1
     for img,sol in pdfDict.items():
         print ("Creating problem "+str(probIdx)+" --> "+img+" with solution: "+str(sol))
         driver = create_new_EM5_pdfquestion(driver,sol,img)
         probIdx+=1

     #driver.save_screenshot("screenshot.png")




#######################################################
def get_default_options(option):
#######################################################
    dicOpt = {}

    #for the type of exam
    if not option.type:
         print ("Please choose the type of exam")
         exit(1)
    else:
        dicOpt['type']= str(option.type)

    #for the file
    if not option.file:
         print ("Please give a file")
         exit(1)
    else:
        dicOpt['file'] = option.file


    return dicOpt

###############################################################
def main():
###############################################################
    #print time
    now = datetime.datetime.now()
    print ("Current date and time : ")
    print (now.strftime("%Y-%m-%d %H:%M:%S"))
    #import optionparser
    option,args = parse(__doc__)
    if not args and not option:
        print ("The script was not configured properly")
        exit(1)

    #set default options
    dicOpt = get_default_options(option)

    #print configuration
    print ("-----------")
    print ("This is the configuration you are using:")
    for k in dicOpt:
        print (str(k)+"\t = "+str(dicOpt[k]))
    print ("-----------")

    thepdffile = dicOpt['file']
    #check if input file exists
    if  not(os.path.isfile(thepdffile)):
        print (thepdffile+" does not exist. Please check.")
        sys.exit(1)

    #create D2L EM test with 5 options from pdf file
    #The pdf file has to have associated tex files
    #so we can extract the correct answers
    #pdffile: plain pdffile with 1 question per page.
    #create_d2l_EM5test(pdffile)
    create_d2l_EM5_pdftest(thepdffile)
    
    #print time
    now = datetime.datetime.now()
    print ("Current date and time : ")
    print (now.strftime("%Y-%m-%d %H:%M:%S"))


#######################################################
if __name__ =='__main__':
#######################################################
     sys.exit(main())


# for div in driver.find_elements_by_tag_name('div'):
#        print (div.get_attribute('id'))

#driver.save_screenshot("screenshot.png")