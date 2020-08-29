#!/usr/bin/python
import sys, os
import unicodedata
import io
import string

#here put the list with the talks' names
talknames = ['Title Talk 1',
             'Title Talk 2',
             'Title Talk 3',
             'Title Talk 4',
             'Title Talk 5',
             'Title Talk 6',
             'Title Talk 7',
             'Title Talk 8',
             'Title Talk 9',
             ]
#duration of each talk in hours:
talkhours = [1,1,1,1,1,1,1,1,1]
#Does the certificate list has a header file to skip?:
HEADER = True
#Name of the tex template (no blank spaces)
PLANTILLATEX = "plantilla_certificado.tex"
#PLANTILLATEX = "Certificate_template.tex"
#String to be used in the file names (no blank spaces)
CERTIFICATETAG = "certifEduCiencia"
#File with the list of names and talks attended (no blank spaces)
NAMELISTINCSV = "lista_certificados.csv"

#######################################################
def insert_the_talks_in_texfile(thetexfile,thetalks):
#######################################################
    tfile = open(thetexfile,"r")
    auxfilename = thetexfile+"_aux"
    auxfile = open(auxfilename,"w")
    lines = tfile.readlines()
    for line in lines:
        if "LASCHARLAS" in line:
            auxfile.write("\\begin{itemize}\n")
            for talk in thetalks:
                auxfile.write("\\item %s\n" % talk)
            auxfile.write("\\end{itemize}\n")
        else:
            auxfile.write(line)
    auxfile.close()
    tfile.close()
    os.system("mv "+auxfilename+" "+thetexfile)
    
#######################################################
def make_latex_certificate(iname,atalks,htalks):
#######################################################
            #remove special characters from iname and then decode it to
        #create name of file stripped from accents (because that's the way
        # god intended it) and encode it again
        tagname = unicodedata.normalize('NFD',''.join(c for c in iname if c.isalnum())).encode('ascii','ignore')
        new_certificate_file = CERTIFICATETAG+"_"+str(tagname,'utf8')+".tex"
        #to replace name in certificate, keep the encoded version
        sed_str = "sed -e 's#\[NOMBRE\]#"+iname+"#g' -e 's#\[LASHORAS\]#"+str(htalks)+"#g' "+PLANTILLATEX+">"+new_certificate_file
        os.system(sed_str)
        #take the new tex and insert the talks
        insert_the_talks_in_texfile(new_certificate_file,atalks)
        #compile in latex
        pdf_str = "pdflatex "+new_certificate_file
        os.system(pdf_str)
        os.system(pdf_str)
        os.system(pdf_str)
        os.system("rm -f "+CERTIFICATETAG+"_*.aux")
        os.system("rm -f "+CERTIFICATETAG+"_*.log")
        os.system("rm -f "+CERTIFICATETAG+"_*.tex")

#######################################################
def make_certificates():
#######################################################
    os.system("rm -f "+CERTIFICATETAG+"_*.*")
    cfile = open(NAMELISTINCSV,"r")
    #cfile = io.open("lista_certificados.csv","r",encoding='utf8')
    lines = cfile.readlines()
    index = 0
    
    for i in lines:
        #Dont use header line if exists
        if (HEADER and index == 0):
            index +=1
            continue
        sline = i.rstrip().split(",")
        #Get the personal information
        iname = sline[0]
        iemail = sline[1]
        #Make a list with the talk info that matches the talk names list
        #in the header. And assuming there is only name and email
        #as personal data, the rest of the entries are talks.  Determine
        #how many:
        italkx = sline[2:]
        ntalks =len(italkx)
        #Make a list of the talks that the person has attended:
        atalks = []
        #Total time in talks
        htalks = 0
        tidx = 0
        for talk in italkx:
            if not talk:
                tidx += 1
                continue
            if talk == "x" or talk == "X":
                atalks.append(talknames[tidx])
                htalks +=talkhours[tidx]
                tidx+=1
            else:
                print("Warning, the talk field for "+iname+" is not empty but it isn't 'x' or 'X' neither.  Please check ...")

        make_latex_certificate(iname,atalks,htalks)
                

    
#######################################################
if __name__ =='__main__':
#######################################################

    make_certificates()

