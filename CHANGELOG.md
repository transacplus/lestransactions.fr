# version1.1
Depuis 2019 le moteur AMF_crawler.py ne fonctionne plus suite au changement des url de l'AMF et d'euronext
Cette version est une modification de AMF_crawler version windows
Pré requis : pdftohtml.exe

*** Correction : ***
- Cette version utilise les nouvelles url amf
- utilisation de yahoo finance pour parser et récupérer ticker, capitalisation
- correctifs sur balises fermantes
- écriture de methodes statiques pour améliorer la lisibilité et evolution du code de la classe AMFdata
- Euros remplacé par EUR et Dollars par USD (norme iso ...) 

*** Evolution : ***

- gestion de la fourchette de récupération des date debut et fin
 > python AMF_crawler.py                      => date du jour
 > python AMF_crawler.py 22122020             => date debut à date du jour
 > python AMF_crawler.py 01122020  01122020   => date debut à date fin
 
 Ajout des colonnes suivantes pour enrichissement :
 Ticker Yahoo
 Date Réception AMF
 Capitalisation
 Commentaires
 

Téléchargé sur lestransactions.fr sous Licence CC-BY-NC-SA		

ISIN	      |  Ticker Yahoo	| Société |	  Déclarant |	                      Date Transaction	| Date Réception|	Nature	Instrument|	Prix	|Volume	|Total	| Total en part de la capitalisation (x%)|	Capitalisation	|Monnaie	|pdf|	Commentaire
FR0013426004	CLA.PA    	CLARANOVA	Sebastien Martin, Executive Vice-President	22/12/2020	22-déc-20	Exercice BSA	Action	        5.3	  39623	  210001	                              0.08	             266.619M    EUR	     https://bdif.amf-france.org/technique/multimedia?docId=f7f56395-057e-4804-b970-08f80e3c98f7&famille=BDIF&bdifId=131527DD0202_2020DD725131	 



