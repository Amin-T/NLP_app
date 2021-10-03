# Financial reports tagger

The purpose of this project is to take financial documents, which are prepared in accordance to the US-GAAP accounting standard, in `.html` format as input, extract financial elements and entities from the text and provide tags in the document as output.

The task of extracting data from the HTML document and labeling the data points is done in 3 separate steps:
1. Extracting the firm specific data, e.g. entity name, legal address, etc.
2. Labeling the monetary and numerical values in the tables, e.g. balance sheet, P&L statement, etc.
3. Labeling the data in the text blocks, i.e. narratives and explanations.

In this document, for every part of the codes, I explain what is already done and what modifications are required. Please refer to the script files for code comments and explanations.

## Files
* requirements.txt            >>> python libraries to be installed
* Taxonomy files              >>>	a folder containing taxonomy xsd files
* Lookup_tagger.py		        >>>	codes of the function which looks for and matches the data with a lookup dictionary, and returns the atgs in an HTML file
* NERmodel_trainer.py	        >>>	functions to create a training data from plain text and train an NER model
* Xbrl_Parser.py		          >>>	function to extract specific data from an XBRL file
* test_HTML_tagger.ipynb	    >>>	jupyter notebook to run and test the Lookup_tagger function
* test_NERmodel_trainer.ipynb >>>	jupyter notebook to run and test the NERmodel_trainer function.

**NOTE:** Before start, install the packages in the requirements.txt file in your Python environment. 

## Firm specific information and monetary values
The first 2 steps mentioned above are done with lookup and match approach. To do so, a dictionary is created in which the keys are the information to be searched in the HTML file, and the values are the tag names corresponding to the taxonomy item names. In the file `Lookup_tagger.py`, a dictionary is created using the firm’s previously filed xbrl and the taxonomy resources. Then for every text in every html element in the current report, the code looks in the lookup dictionary and tags the data if it finds a match.

The information related to the specific firm such as name, legal address, country, etc. is extracted from the most recent filed xbrl report (if it exists). Assuming the firm’s most recent HTML report with inline xbrl tags exists, `Xbrl_Parser.py` module is used.
The file `Xbrl_Parser.py` uses *py-xbrl* library to parse the previously filed xbrl file and returns the data and facts specified by the user. 

### To be considered and/or modified:
1. Which firm facts should be extracted as firm specific information.
2. Labeling other numerical data in tables
3. Extracting money currencies, scale and periods from tables

## Customized  NER Tagger
The 3rd step for a comprehensive HTML tagger is training and implementing a custom NER on the text blocks and narratives. The file `NERModel_trainer.py` is used for this purpose. In this file a custom NER model is trained using spaCy. For detailed explanation please refer to codes and this link. 
This file also has a module for creating a training data set. The training data set for updating the spaCy’s NER engine should look like below. 

```
TRAIN_DATA = [
    ('Who is Nishanth?', {
        'entities': [(7, 15, 'PERSON')]
    }),
     ('Who is Kamal Khumar?', {
        'entities': [(7, 19, 'PERSON')]
    }),
    ('I like London and Berlin.', {
        'entities': [(7, 13, 'LOC'), (18, 24, 'LOC')]
    })
]
```

The function `build_TrainData` takes a plain text and a list of labels. Then, then it looks in the text and in every sentence in the text, it looks for the corresponding text related to the labels and returns a tuple looking like above if it finds any.
Then the created training data is passed into the `train_custom_NER` function to train the model.
The main problem in this part is preparing comprehensive and accurate training data. After that, it is easily implemented on the report to label the data.

### To be considered and/or modified:
1. Creating an appropriately big training dataset.
2. Training the NER model on the training dataset
3. Developing the codes which looks in the text blocks in the html file and labels the data


## Resources
https://www.sec.gov/ix?doc=/Archives/edgar/data/310826/000031082620000032/plico-20200930.htm 
https://www.codeproject.com/Articles/1227765/Parsing-XBRL-with-Python 
https://pypi.org/project/py-xbrl/ 
https://xmlschema.readthedocs.io/en/latest/ 
https://www.crummy.com/software/BeautifulSoup/bs4/doc/ 
https://www.sec.gov/structureddata/osd-inline-xbrl.html 
https://xbrl.us/xbrl-taxonomy/2021-us-gaap/ 
https://www.fasb.org/jsp/FASB/Page/SectionPage&cid=1176175721628?mc_cid=45bf17e032&mc_eid=6cf248d39e 
https://medium.com/analytics-vidhya/creating-own-name-entity-recognition-using-bert-and-spacy-tourism-data-set-c5ee1c2955a2 
https://docs.tagtog.net/ 
https://towardsdatascience.com/custom-named-entity-recognition-using-spacy-7140ebbb3718 
https://towardsdatascience.com/train-ner-with-custom-training-data-using-spacy-525ce748fab7 
https://www.machinelearningplus.com/nlp/training-custom-ner-model-in-spacy/ 
https://spacy.io/usage/rule-based-matching 
https://github.com/gandersen101/spaczz 

