import subprocess
import re
import urllib.request
import csv
import time
import datetime
from urllib.request import urlopen
import requests
import sqlite3

from sqlite3 import Error

import smtplib
import json
import sys
#from data.subscriptions import subscriptions
#from local.env import MAIL_PASSWD, BASE_DIR, SMTP_ADDRESS
from localenv import  BASE_DIR

class AMFdata(object):

    @staticmethod
    def get_yahoo_ticker(isin) :
        "recupere le code yahoo a partir du code isin"
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {'q': isin, 'quotesCount': 1, 'newsCount': 0}

        r = requests.get(url, params=params)
        data = r.json()
        #print('code yahoo :')
        ticker = data['quotes'][0]['symbol']
        return ticker

    @staticmethod
    def get_part_capitalisation(ticker_yahoo,total):
        """Recupere la capitalisation via Yahoo pour caluculer le part du capital"""
           
        capifind = AMFdata.get_market_value(ticker_yahoo)
        print('==========>capi')
        print(capifind)
        capifind = capifind.replace(',', '.')
        capifloat = 0
        capifindsave = capifind

        if capifind.find('M') != -1: 
            capifind = capifind.replace('M', '')
            capifloat= float(capifind) * 1000000
            
        if capifind.find('B') != -1:
            capifind = capifind.replace('B', '')
            capifloat= float(capifind) * 1000000000   
        # Calcul de la part du capital echange
        partcap = 100 * float( total) / float(capifloat)
        partcap = round(partcap,2)
        if partcap < 0.01:
            partcap= 0.0
        print('part en %')
        
        t =( partcap , capifindsave)
        print (t)
        return ( partcap , capifindsave)



    @staticmethod
    def get_market_value(ticker_yahoo) :
        """ récupere la capi de la valeur via yahoo finance"""
        
        url = "https://fr.finance.yahoo.com/quote/" +  str(ticker_yahoo)
        print (url)
        session = requests.Session()
        session.cookies['cookiewall'] = 'yes'
        f  = session.get(url)  
        if f.status_code == 404:
            print ('404')   
        return AMFdata.get_Yahoo_marketcap(f.text)


    @staticmethod
    def get_Yahoo_marketcap(html):
        """Retourne la capitalisation de la valeur"""

        # data-test="MARKET_CAP-value" data-reactid="80"><span class="Trsdu(0.3s) " data-reactid="81">188,674M</span>
        theseregexp = "(MARKET_CAP-value)(.+?)(<span class=)(.+?)(</span>)"  # pattern for search result page
        pattern = re.compile(theseregexp)
        content = re.findall(pattern, html)  # get a list of all the results on result page
        (a,b,c,d,e) = content[0]
        resu =re.split(' ', d)[2]
        capi = (re.split('>',resu)[1])
        return capi
       
    @staticmethod
    def get_end_page(html):
        try:
            
            """Retourne le numero de la derniere page"""
            # <span class="page"><a href="https://bdif.amf-france.org/Resultat-de-recherche-BDIF?PAGE_NUMBER=3&amp;LANGUAGE=fr&amp;BDIF_NOM_P
            theseregexp = "(class=\"page\">)(.+?)(PAGE_NUMBER=)(.+?)(&amp;formId=)"  # pattern for search result page
            pattern = re.compile(theseregexp)
            content = re.findall(pattern, html)  # get a list of all the results on result page
            #print (content)
            return list(content[-1])[-2]
        except Exception as e:
            # une seul page
            return 1

    @staticmethod
    def get_date_now():
        """Retourne la date du jour au format [day, month, year] """

        if len(str(datetime.datetime.today().day)) == 1:
            day = ''.join(('0', str(datetime.datetime.today().day)))
        else:
            day = str(datetime.datetime.today().day)
        if len(str(datetime.datetime.today().month)) == 1:
            month = ''.join(('0', str(datetime.datetime.today().month)))
        else:
            month = str(datetime.datetime.today().month)
        year = str(datetime.datetime.today().year)
        return [day, month, year]

    @staticmethod
    def convert_pdf2html():
        """ convert file to html with pdftohtml external tool"""   

        # TODO Linux
        bash_command = ''.join(("pdftohtml.exe ", BASE_DIR+'test.pdf'))
        subprocess.call(bash_command, shell=True, stdout=subprocess.PIPE)
        """
        subprocess.call('rm '+BASE_DIR+'test.html', shell=True)
        subprocess.call('rm '+BASE_DIR+'test.pdf', shell=True)
        subprocess.call('rm '+BASE_DIR+'test_ind.html', shell=True)
        """
        subprocess.call('del ' + BASE_DIR + 'test.html', shell=True)
        subprocess.call('del ' + BASE_DIR + 'test.pdf', shell=True)
        subprocess.call('del ' + BASE_DIR + 'test_ind.html', shell=True)



    @staticmethod
    def parseurAMF(content):
        init_isin=''
        ticker_yahoo=''
        for cont in content:  # navigate in each result
            doc_search = "https://bdif.amf-france.org" + cont[0] + cont[1]
            #print (doc_search)
            
            try:  
                f = urllib.request.urlopen(doc_search)
            except urllib.error.URLError as e:
                print(e.reason)      
                print ("erreur 404 pour " + doc_search)
                continue
            except Exception as err :
                print(err.reason)      
                print ("autre erreur " + doc_search)
                continue

            doc_file = f.read().decode('utf-8')
            # ge the pattern for file link
            theseregexp = "(/technique/multimedia?)(.+?)(>Consulter le document)"
            pattern = re.compile(theseregexp)
            doc_content = re.findall(pattern, doc_file)
            #print (doc_content)
            # prepare all regexp
            
            isinregex = "[A-Z][A-Z][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"  # ISIN
            isinpattern = re.compile(isinregex)
            nameregex = "NOM :"  # company name
            namepattern = re.compile(nameregex)
            theseregexp = "</b>(.+?)<br>"  # global match regexp
            pattern = re.compile(theseregexp)
            
            datalist = [{"Nature": "NATURE DE LA TRANSACTION"},
                        {"Prix": "PRIX :"},
                        {"Prix unitaire": "PRIX UNITAIRE :"},
                        {"Volume": "VOLUME :"},
                        {'Date': 'DATE DE LA TRANSACTION'},
                        {'Date reception': 'DATE DE RECEPTION DE LA NOTIFICATION :'}, 
                        {"Instrument": "INSTRUMENT FINANCIER :"},
                        {"Commentaires": "COMMENTAIRES :"}]
            
            

            for doc_cont in doc_content:
                try:
                    # get the file and convert it to html
                    pdf_address = "https://bdif.amf-france.org" + doc_cont[0] + doc_cont[1]
                    #print (pdf_address)

                    #i=i+1
                    #print (str(i))
                    final_pdf = urllib.request.urlretrieve(
                        pdf_address[:-1], BASE_DIR+'test'  +'.pdf')  # download file

                    AMFdata.convert_pdf2html()                  

                    

                    # open html file and get a first read to analyze the number or transactions in file
                    print ('open html file and get a first read to analyze the number or transactions in file')
                    transac_page = []
                   
                    with open(BASE_DIR+"tests.html", 'r') as file:
                        i = 0
                        k = 0
                        for line in file:
                            content = re.findall("DETAIL DE LA TRANSACTION", line)

                            if content:
                                try:
                                    transac_page.append(i)
                                except KeyError:
                                    transac_page = [i]
                            isin = re.findall(isinpattern, line)
                            if isin:
                                isin_name = re.findall(isinpattern, line)  # match ISIN
                                #print(isin)
                            name = re.findall(namepattern, line)
                            if name:
                                company_name = re.findall(pattern, line)  # match company name
                                print (company_name)
                            if k == 1:
                                manager_name = re.findall(re.compile('(.+?)<br>'), line)  # match manager name
                                k = 0
                            manager = re.findall(
                                "<b>NOM /FONCTION DE LA PERSONNE EXERCANT DES RESPONSABILITES DIRIGEANTES OU DE LA<br>PERSONNE ETROITEMENT LIEE :</b><br>", line)
                            if manager:
                                k += 1
                            i += 1
                        if len(transac_page) == 0:
                            transac_page.append(0)
                        transac_page.append(i)  # get a list of all the lines

                    #print (transac_page)
                    # parse file to match all the global regexp list
                   
                    for transac_line in range(len(transac_page) - 1):
                        op = {}
                        op['pdf'] = [pdf_address[:-1]]
                        #print (op['pdf'])
                        for data in datalist:
                            for key, value in data.items():
                                #print (key, value)
                                with open(BASE_DIR+"tests.html", 'r') as file:
                                    i = 0
                                    for line in file:
                                        #print ('line' + line)

                                        if i >= transac_page[transac_line] and i <= transac_page[transac_line + 1]:
                                            content = re.findall(value, line)
                                            if content:
                                                try:
                                                    op[key].append(re.findall(pattern, line)[0])
                                                    #print ('op[key].append(re.findall(pattern, line)[0])')
                                                except KeyError:
                                                    op[key] = re.findall(pattern, line)
                                        else:
                                            #print ('pas de valeur trouvé')
                                            pass
                                        i += 1
                        op['Société'] = company_name
                        op['ISIN'] = isin_name
                        op['Déclarant'] = manager_name
                        print(op['Société'])
                        if len(op['Commentaires']) ==0 :
                            op['Commentaires']=' '
                        print('Commentaire:')
                        print(op['Commentaires'])
                        # treat al the specific cases
                        try:
                            if float(op["Prix"][0][:-5].replace(' ', '')) == 0:
                                op["Prix"] = [float(op["Prix unitaire"][0][:-5].replace(' ', ''))]
                            elif float(op["Prix"][0][:-5].replace(' ', '')) > 2 * float(op["Prix unitaire"][0][:-5].replace(' ', '')):
                                op["Total"] = [float(op["Prix"][0][:-5].replace(' ', ''))]
                            else:
                                op["Prix"] = [float(op["Prix"][0][:-5].replace(' ', ''))]
                            op['Monnaie'] = ['EUR']
                        except ValueError:  # dollar des etat-unis
                            if float(op["Prix"][0][:-22].replace(' ', '')) == 0:
                                op["Prix"] = [float(op["Prix unitaire"][0][:-22].replace(' ', ''))]
                            else:
                                op["Prix"] = [float(op["Prix"][0][:-22].replace(' ', ''))]
                            op['Monnaie'] = ['USD']
                        op["Volume"] = [max([float(op["Volume"][i].replace(' ', ''))
                                                for i in range(len(op["Volume"]))])]
                        try:
                            op["Total"]
                            op["Prix"] = [op["Total"][0] / op["Volume"][0]]
                        except KeyError:
                            op["Total"] = [op["Volume"][0] * op["Prix"][0]]
                        del op["Prix unitaire"]
                        for key, value in op.items():
                            op[key] = value[0]

                        # convert transaction date to YYYY-MM-DD format for the db to be able to sort it
                        month = {'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04', 'mai': '05', 'juin': '06',
                                    'juillet': '07', 'août': '08', 'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'}
                        op['Date'] = '-'.join((op['Date'][-4:], month[op['Date'][3:-5]], op['Date'][:2]))
                        print('fin bloc')
                        
                        print ('===AVANT======================================================')
                        #op['Part du capital']  = str(AMFdata.get_part_capitalisation(op['ISIN'] , op["Total"]))
                        if op['ISIN'] != init_isin :
                            print ("zzzzzzzzzzz")
                            print (init_isin)
                            ticker_yahoo = AMFdata.get_yahoo_ticker(op['ISIN'])
                            init_isin = op['ISIN']
                            print (ticker_yahoo)
                        p,c = AMFdata.get_part_capitalisation( ticker_yahoo , op["Total"])
                        op['Part du capital'] =str(p)
                        
                        print ('=========================================================')
                        capitalisation=str(c)
                        print (op['Part du capital'])

                        # connect to the db and save the data
                        # TODO gerer \\ win unix
                        conn = sqlite3.connect(BASE_DIR +'stock_data\\amf.db')

                        c = conn.cursor()
                        print('TATA')
                        print ('isin '+ op["ISIN"])
                        """
                        print ('Déclarant '+ op["Déclarant"])
                        print ('Société '+ op["Société"])
                        print ('Date '+ op["Date"])
                        print ('Date réception '+ op["Date reception"])
                        print ('Nature '+ op["Nature"])
                        print ('Instrument '+ op["Instrument"])
                        print ('Prix '+ op["Prix"])
                        print ('Volume '+ str(op["Volume"]))
                        print ('Total '+ str(op["Total"]))
                        print ('Monnaie '+ op["Monnaie"])
                        print ('pdf '+ op["pdf"])
                        """
                        #op["Commentaires"]= 'test'
                        print ('avant sql')
                        sql= [op["ISIN"], op["Société"], op["Déclarant"], op["Date"],op["Date reception"] ,op["Nature"], op["Instrument"], op["Prix"], int(op["Volume"]), int(op["Total"]), op['Part du capital'], 'capitalisation', op['Monnaie'], op["pdf"], 'test']
                        print (sql)
                        c.execute("INSERT INTO stocks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [op["ISIN"], ticker_yahoo, op["Société"], op["Déclarant"], op["Date"],op["Date reception"] ,op["Nature"], op["Instrument"], op["Prix"], int(op["Volume"]), int(op["Total"]), op['Part du capital'], capitalisation, op['Monnaie'], op["pdf"],op['Commentaires']])
                        conn.commit()
                        """
                        for user in subscriptions.keys():
                            for isin, capi_isin in subscriptions[user].items():
                                if isin != 'global' and isin != '0' and isin != 'Vide':
                                    if op['ISIN'] == isin.replace(' ', '') and op['Part du capital'] >= float(capi_isin):
                                        Mail.send_mail(op, user)
                                        print('mail envoyé :', op['ISIN'], user)
                            try:
                                subscriptions[user]['global']
                            except KeyError:
                                subscriptions[user]['global'] = 0
                            capi = float(subscriptions[user]['global'])
                            if capi == 0:
                                continue
                            elif float(op['Part du capital']) > capi and float(op['Part du capital']) < 100:
                                Mail.send_mail(op, user)
                                print('mail envoyé :', op['ISIN'], user)
                        """
                except:
                    print('error')
                    pass

    def format_date(datejjmmaa):
        jjmmaaaa = list(datejjmmaa)  
        jj=''.join(jjmmaaaa[0:2])
        mm= ''.join(jjmmaaaa[2:4])
        aaaa= ''.join(jjmmaaaa[4:8])
        return [jj,mm,aaaa]

    def get_date_debut_fin(argv) :

        if len(sys.argv) == 1:
            # par défaut, pas d'argument
            # date now du jour
            datedebut = AMFdata.get_date_now()
            date = datedebut 
        if len(sys.argv) == 2:
            date_debut_jjmmaaaa=sys.argv[1]
            datedebut =AMFdata.format_date(date_debut_jjmmaaaa)
            # date fin => now du jour
            date = AMFdata.get_date_now()
         
        if len(sys.argv) == 3:
            date_debut_jjmmaaaa=sys.argv[1]
            datedebut =AMFdata.format_date(date_debut_jjmmaaaa)
            date_fin_jjmmaaaa=sys.argv[2]
            date =AMFdata.format_date(date_fin_jjmmaaaa)
        return (datedebut, date)

    def run():
        # format date en ligne de commande jjmmaaaa
        # gestion d une periode de recuperation de data
        datedebut=[]
        date=[]
        datedebut, date = AMFdata.get_date_debut_fin(sys.argv)
        
        # AVANT for page in range(1, page_number):  # loop on pages  class="page"  /   <span class="page"><a href="https://bdif.amf-france.org/Resultat-de-recherche-BDIF?PAGE_NUMBER=6608&amp;formId
        page_number = 1
        currentpage = 1
        #pour test
        #datedebut =  ['01','08','2020']
        #date =       ['15','08','2020']
        
        while currentpage <= page_number:
            """
             & subFormId = dd & BDIF_TYPE_INFORMATION = BDIF_TYPE_INFORMATION_DECLARATION_DIRIGEANT & BDIF_RAISON_SOCIALE = & bdifJetonSociete = & BDIF_NOM_PERSONNE = & REFERENCE = & BDIF_TYPE_DOCUMENT = & DATE_PUBLICATION = 01 % 2
            F06 % 2
            F2020 & DATE_OBSOLESCENCE = 17 % 2
            F12 % 2
            F2020 & valid_form = Lancer + la + recherche & isSearch = true
            appel 2eme page
               https://bdif.amf-france.org/Resultat-de-recherche-BDIF?PAGE_NUMBER=2&formId=BDIF&LANGUAGE=fr&BDIF_NOM_PERSONNE=&valid_form=Lancer+la+recherche&DATE_OBSOLESCENCE=&BDIF_TYPE_DOCUMENT=&BDIF_TYPE_INFORMATION=BDIF_TYPE_INFORMATION_DECLARATION_DIRIGEANT&bdifJetonSociete=&subFormId=dd&DOC_TYPE=BDIF&BDIF_RAISON_SOCIALE=&isSearch=true&REFERENCE=&DATE_PUBLICATION=
            """
            amf_search="https://bdif.amf-france.org/Resultat-de-recherche-BDIF?PAGE_NUMBER=" + str(currentpage) + "&formId=BDIF&DOC_TYPE=BDIF&LANGUAGE=fr&subFormId=dd&BDIF_TYPE_INFORMATION=BDIF_TYPE_INFORMATION_DECLARATION_DIRIGEANT&BDIF_RAISON_SOCIALE=&bdifJetonSociete=&BDIF_NOM_PERSONNE=&REFERENCE=&BDIF_TYPE_DOCUMENT=&DATE_PUBLICATION="\
            + datedebut[0] + "%2F" + datedebut[1] + "%2F" + datedebut[2]+"&DATE_OBSOLESCENCE="+date[0] + "%2F" + date[1] + "%2F" + date[2] \
            + "&valid_form=Lancer+la+recherche&isSearch=true"

            # les pages https://bdif.amf-france.org/Resultat-de-recherche-BDIF?PAGE_NUMBER=2&formId=BDIF&LANGUAGE=fr&BDIF_NOM_PERSONNE=&valid_form=Lancer+la+recherche&DATE_OBSOLESCENCE=16%2F12%2F2020&BDIF_TYPE_DOCUMENT=&BDIF_TYPE_INFORMATION=BDIF_TYPE_INFORMATION_DECLARATION_DIRIGEANT&bdifJetonSociete=&subFormId=dd&DOC_TYPE=BDIF&BDIF_RAISON_SOCIALE=&isSearch=true&REFERENCE=&DATE_PUBLICATION=16%2F12%2F2020
            #amf_search = "http://www.amf-france.org/Resultat-de-recherche-BDIF.html?PAGE_NUMBER=" + page_number + "&formId=BDIF&LANGUAGE=fr&BDIF_NOM_PERSONNE=&valid_form=Lancer+la+recherche&DATE_OBSOLESCENCE=" + date[0] + "%2F" + date[1] + "%2F" + date[
            #    2] + "&BDIF_TYPE_INFORMATION=BDIF_TYPE_INFORMATION_DECLARATION_DIRIGEANT&bdifJetonSociete=&subFormId=dd&DOC_TYPE=BDIF&BDIF_RAISON_SOCIALE=&isSearch=true&REFERENCE=&DATE_PUBLICATION=" + date[0] + "%2F" + date[1] + "%2F" + date[2]
            #print (amf_search)
            
            #sys.exit()
            session = requests.Session()
            session.cookies['cookiewall'] = 'yes'
            f  = session.get(amf_search)  # connect to amf website
            if f.status_code == 404:
                break  # if page doesnt exist, go to next loop
            amf_search_result = f.text
            #
            #print (amf_search_result)
            #
            if page_number == 1:
                page_number = int(AMFdata.get_end_page(amf_search_result))
            #print (page_number)
            #import sys
            #sys.exit()
            """
            < a
            href = "/technique/proxy-lien?docId=602427DD0202_2020DD724206&famille=BDIF&isSearch=true&lastSearchPage=https%3A%2F%2Fbdif.amf-france.org
            %2FmagnoliaPublic%2Famf%2FResultat-de-recherche-BDIF%3FPAGE_NUMBER%3D2%26formId%3DBDIF%26LANGUAGE%3Dfr%26BDIF_NOM_PERSONNE
            %3D%26valid_form%3DLancer%2Bla%2Brecherche%26DATE_OBSOLESCENCE%3D16%252F12%252F2020%26BDIF_TYPE_DOCUMENT
            %3D%26BDIF_TYPE_INFORMATION%3DBDIF_TYPE_INFORMATION_DECLARATION_DIRIGEANT%26bdifJetonSociete%3D%26subFormId
            %3Ddd%26DOC_TYPE%3DBDIF%26BDIF_RAISON_SOCIALE%3D%26isSearch%3Dtrue%26REFERENCE%3D%26DATE_PUBLICATION%3D16%252F12
            %252F2020&langue=fr&xtmc=Declaration-des-dirigeants&xtcr=11"

            class ="lien_plus3" title="consulter : Déclaration des dirigeants BIOCORP PRODUCTION" target ="_self" > Consulter le document < / a >
            """
            toto= amf_search_result
            theseregexp = "(/technique/proxy-lien?)(.+?)(class=)"  # pattern for search result page
            pattern = re.compile(theseregexp)
            #content = re.findall(pattern, amf_search_result)  # get a list of all the results on result page
            content = re.findall(pattern, toto)  # get a list of all the results on result page
            #print (content)

            AMFdata.parseurAMF(content)
            currentpage += 1  # on passe a la page suivante

class CsvWriter(object):

    def run():
        print('writing csv')
       
        #TODO
        #conn = sqlite3.connect(BASE_DIR + 'stock_data/amf.db')
        conn = sqlite3.connect(BASE_DIR+'stock_data\\amf.db')
        c = conn.cursor()
        data = c.execute('''SELECT * FROM stocks''')
        #csvWriter = csv.writer(open(BASE_DIR+"stock_data/data.csv", "w"), delimiter=';')
        csvWriter = csv.writer(open(BASE_DIR + "stock_data\\data.csv", "w",newline=''), delimiter=';')
        csvWriter.writerow(['Téléchargé sur lestransactions.fr sous Licence CC-BY-NC-SA'])
        csvWriter.writerow(["ISIN","Ticker Yahoo", "Société", "Déclarant", "Date Transaction","Date Réception" , "Nature", "Instrument",
                            "Prix", "Volume", "Total", "Total en part de la capitalisation (x%)","Capitalisation", 'Monnaie', "pdf","Commentaire"])
        for row in data:
            csvWriter.writerow(row)
        print('done')


class Tradingdata(object):
    """ TODO a migrer url nexiste plus"""
    def run():
        print('getting trading data')
        conn = sqlite3.connect(BASE_DIR+'stock_data/amf.db')
        c = conn.cursor()
        data = c.execute('''SELECT DISTINCT isin FROM stocks''')
        tradedict = {}
        for da in data:
            try:
                euronext = 'https://www.euronext.com/fr/nyx_eu_listings/real-time/quote?isin=' + da[0] + '&mic=XPAR'
                f = requests.get(euronext)  # connect to euronext website
                file = f.text
                cours = '(<td>&euro;)(.+?)(&nbsp;)(.+?)(</td>)'
                cours2 = re.compile(cours)
                coursfind = re.findall(cours2, file)
                tradedict[da[0]] = float(coursfind[0][1].replace(',', '.'))
                print(da[0])
            except:
                try:
                    time.sleep(5)
                    euronext = 'https://www.euronext.com/fr/nyx_eu_listings/real-time/quote?isin=' + \
                        da[0] + '&mic=XPAR'
                    f = requests.get(euronext)  # connect to euronext website
                    file = f.text
                    cours = '(<td>&euro;)(.+?)(&nbsp;)(.+?)(</td>)'
                    cours2 = re.compile(cours)
                    coursfind = re.findall(cours2, file)
                    tradedict[da[0]] = float(coursfind[0][1].replace(',', '.'))
                    print(da[0])
                except:
                    print('error :', da[0])
                    pass
            time.sleep(2)
        with open(BASE_DIR+'stock_data/trade.json', 'w+') as trade:
            json.dump(tradedict, trade)
        print('done')


class Mail(object):

    def send_mail(op, email):
        mailserver = smtplib.SMTP(SMTP_ADDRESS)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.login("lestransactions@alwaysdata.net", MAIL_PASSWD)
        msg = "\r\n".join([
            "Subject: [LesTransactions.fr] Alerte email " + str(op['Société']),
            "Bonjour,",
            " ",
            "Vous recevez cet e-mail en raison de la transaction suivante : ",
            " ",
            "ISIN : " + str(op['ISIN']),
            "Societe : " + str(op["Société"]),
            "Declarant : " + str(op["Déclarant"]),
            "Date de transaction : " + str(op["Date"]),
            "Nature : " + str(op["Nature"]),
            "Instrument : " + str(op["Instrument"]),
            "Prix : " + str(op["Prix"]),
            "Volume : " + str(int(op["Volume"])),
            "Montant total : " + str(int(op["Total"])),
            "Total en part de la capitalisation (x%) : " + str(op['Part du capital']),
            "Monnaie : " + str(op['Monnaie']),
            "Lien : " + str(op["pdf"]),
            " ",
            "Pour vous désabonner, rendez-vous dans votre espace personnel : https://lestransactions.fr/login"
        ])
        mailserver.sendmail("robot@lestransactions.fr", email, msg.encode('utf-8'))
        return True





def create_connection(db_file):
    """ create a database connection to a SQLite database """
    create_table_sql = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
        create_table_sql="CREATE TABLE stocks ( \
        ISIN TEXT NOT NULL,\
        Ticker TEXT,\
        Societe TEXT  ,\
        Déclarant TEXT  ,\
        Date TEXT  ,\
        Date_reception TEXT,\
        Nature TEXT,\
        Instrument TEXT,\
        Prix TEXT,\
        Volume INTEGER ,\
        Total INTEGER ,\
        Part_du_capital TEXT,\
        Capitalisation TEXT,\
        Monnaie TEXT,\
        pdf TEXT ,\
        commentaires TEXT);"

        c = conn.cursor()
        c.execute(create_table_sql)

    except Error as e:
        print(e)
    finally:
        if conn:
            conn.close()




if __name__ == '__main__':
   
    create_connection(BASE_DIR +'stock_data\\amf.db')
   
    jjmmaaa =[]
    print ('Number of arguments:', len(sys.argv), 'arguments.')
    print ('Argument List:', str(sys.argv))
    """
    url_erreur = "https://bdif.amf-france.org/technique/proxy-lien?docId=321607DD0202_2020DD706123&famille=BDIF&isSearch=true&lastSearchPage=https%3A%2F%2Fbdif.amf-france.org%2FmagnoliaPublic%2Famf%2FResultat-de-recherche-BDIF%3FPAGE_NUMBER%3D2%26formId%3DBDIF%26LANGUAGE%3Dfr%26BDIF_NOM_PERSONNE%3D%26valid_form%3DLancer%2Bla%2Brecherche%26DATE_OBSOLESCENCE%3D26%252F10%252F2020%26BDIF_TYPE_DOCUMENT%3D%26BDIF_TYPE_INFORMATION%3DBDIF_TYPE_INFORMATION_DECLARATION_DIRIGEANT%26bdifJetonSociete%3D%26subFormId%3Ddd%26DOC_TYPE%3DBDIF%26BDIF_RAISON_SOCIALE%3D%26isSearch%3Dtrue%26REFERENCE%3D%26DATE_PUBLICATION%3D22%252F10%252F2020&langue=fr&xtmc=Declaration-des-dirigeants&xtcr=20"
    try:  
        f = urllib.request.urlopen(url_erreur)
    except urllib.error.URLError as e:
        print(e.reason)      
        print ("erreur 404")
    print ("et on continue !")
    """
   
    """
    #capifind =AMFdata.get_market_value('FR0013399359')
    p,c = AMFdata.get_part_capitalisation('FR0013399359','336600')
    print (p)
    print (c)
    """
    """
    capifind = capifind.replace(',', '.')
    capifloat=0
    print (capifind)
    
    if capifind.find('M') != -1: 
        capifind = capifind.replace('M', '')
        capifloat= float(capifind) * 1000000
        
    if capifind.find('B') != -1:
        capifind = capifind.replace('B', '')
        capifloat= float(capifind) * 1000000000   
    
    partcap = 100 * float('336600') / float(capifloat)
    partcap = round(partcap,2)
    if partcap < 0.01:
        partcap= 0
    
    print (partcap)
    #print (AMFdata.get_market_value(isin))
    """

    AMFdata.run()  # launch AMF crawler and save in DB
    
    CsvWriter.run()  # export to csv

    #Tradingdata.run()  # Get trading data from euronext