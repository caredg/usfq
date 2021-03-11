import sys, os
import unicodedata
import string

#Does the certificate list has a header file to skip?:
HEADER = False
#String to be used in the file names (no blank spaces)
CERTIFICATETAG = "certifCMSMasterclass"
#File with the list of names and talks attended (no blank spaces)
NAMELISTINCSV = "lista_certificados.csv"
#Name of the tex template (no blank spaces)
PLANTILLATEX = "plantilla_certificado.tex"
#Should we concatenate all output pdf certificates?
CATPDFTK = True


#######################################################
def make_latex_certificate(iname):
#######################################################
        #remove special characters from iname and then decode it to
        #create name of file stripped from accents (because that's the way
        # god intended it) and encode it again
        tagname = unicodedata.normalize('NFD',''.join(c for c in iname if c.isalnum())).encode('ascii','ignore')
        new_certificate_file = CERTIFICATETAG+"_"+str(tagname,'utf8')+".tex"
        #to replace name in certificate, keep the encoded version
        sed_str = "sed -e 's#\[Nombre\]#"+iname+"#g' "+PLANTILLATEX+">"+new_certificate_file
        print (sed_str)
        os.system(sed_str)
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
        iname = i.strip('\n')
        make_latex_certificate(iname)

    if (CATPDFTK):
            print ("Merging all pdfs ....")
            os.system("pdftk "+CERTIFICATETAG+"_*.pdf cat output "+CERTIFICATETAG+"_all.pdf")

#######################################################
if __name__ =='__main__':
#######################################################

    make_certificates()
