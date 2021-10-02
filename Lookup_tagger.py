
# Import libraries
from bs4 import BeautifulSoup
import xmlschema
import glob
from zipfile import ZipFile
from io import BytesIO
import requests
import pandas as pd
import re
from rapidfuzz import fuzz
from rapidfuzz import process
from Xbrl_Parser import read_xbrl

""" FUNCTIONS """

def has_name(tag):
    """
    Function to filter html elements having "name" attribute
    """
    return tag.has_attr('name')


def remove_unicode(string):
    """
    Function to remove Unicode characters in a string
    """
    string_unicode = re.sub(pattern='(\xa0\s*)+', repl=' ', string=string)
    string_encode = string_unicode.encode("ascii", "xmlcharrefreplace")
    string_decode = string_encode.decode()
    string_decode = re.sub(pattern='(&#\d+;\s*)+', repl=' ', string=string_decode)
    return string_decode


def strDetached(string, split=True, split_by=':'):
    """
    Function to detache strings
    """
    if split:
        string = string.split(split_by)[-1]
    words = []
    start = 0
    if string.isupper():
        detached_string = string
    else:
        for i, c in enumerate(string[1:]):
            if c.isupper():
                end = i
                words.append(string[start:end+1])
                start = end + 1
        words.append(string[start:])
        detached_string = ' '.join(words)
    return detached_string


def LoadHTML(html_file):
    """
    Read an html file using bs4 html parser
    """
    with open(html_file, 'rb') as f:
        html_doc = f.read()

    parsed_html = BeautifulSoup(html_doc, 'html.parser')

    print(f'File "{html_file}" is loaded.')
    return parsed_html


def firmDict(xbrl_FilePath, firm_facts):
    """
    Creates a lookup dictionary from tagged monetary data in tables and the firm specific facts in previously filed xbrl report.
    Returns a list of [tables_dict, firm_dict]
    """
    tables_dict = {}
    firm_dict = {}

    # regex is used to find monetary values in tables and add their row titles to lookup_dict 
    money_pattern = '\s*\(?(\d+(,\d+)+)\)?\s*' #pattern to match monetary values

    # Find all the 'table' elements in the parsed xbrl report
    parsed_xbrl = LoadHTML(html_file=xbrl_FilePath)
    tables = parsed_xbrl.body.find_all('table')

    # Loop over the tables and add their row titles to lookup_dict
    for tbl in tables:
        # Get all tagged (labaled) data in the tables
        tags = tbl.find_all(has_name)
        for tag in tags:
            label = tag['name'].split(':')[-1] #remove name prefixes
            if tag.string:
                # Remove unicode strings and HTML characters
                string = remove_unicode(tag.string).strip()

                # Check if the fact type is numeric
                if tag.name == 'ix:nonfraction':
                    # Check if the fact is a monetary value
                    if re.fullmatch(pattern=money_pattern, string=string):
                        try:
                            # If the monatry value is in a table, use the row title as fact
                            tbl_row = tag.find_parent('tr')
                            fact = remove_unicode(tbl_row.td.text).strip()
                            tables_dict[fact] = label
                        except:
                            pass

    if firm_facts:
        # Add values from selected_facts (firm specific facts) to lookup_dict
        firm_facts = read_xbrl(file_path=xbrl_FilePath, selected_facts=firm_facts)
        for item in firm_facts:
            firm_dict[firm_facts[item]['value']] = item

    print("Firm specific lookup dictionary created from the previously filed xbrl report")
    return [tables_dict, firm_dict]
    
def get_tag_data(element, Tags_dict, name, Elements_df=None, References_df=None, xsd_dict=None):
    """
    Funcion to get required data from taxonomy resources based on tag name, and add the tag and the data to the Tags_dict.
    """
    # Define a unique "id" for the tag
    # id: line number - position of the start tag within a line - label
    if element.has_attr('id'):
        id = element['id']
    else:
        id = str(element.sourceline) + '-' + str(element.sourcepos) + '-' + name
                    
    Tags_dict[id] = {'Attributes': {},
                    'Labels': {},
                    'References': {}}

    Tags_dict[id]['Attributes']['Tag'] = name
                                    
    # Get other information from the taxonomy resources based on tag's "name"
    if (Elements_df is not None) and (References_df is not None):
        name_Elements_df = Elements_df[Elements_df['name'] == name]
        if not name_Elements_df.empty:
            Tags_dict[id]['Attributes']['Type'] = name_Elements_df['type'].values[0]
            Tags_dict[id]['Labels']['Documentation'] = name_Elements_df['documentation'].values[0]
            Tags_dict[id]['Labels']['Label'] = name_Elements_df['label'].values[0]
        name_References_df = References_df[References_df['name'] == name]
        if not name_References_df.empty:
            Tags_dict[id]['References']['Name'] = name_References_df['Name'].values[0]
            Tags_dict[id]['References']['Number'] = name_References_df['Number'].values[0]
            Tags_dict[id]['References']['Publisher'] = name_References_df['Publisher'].values[0]
            Tags_dict[id]['References']['Section'] = name_References_df['Section'].values[0]
            Tags_dict[id]['References']['Subsection'] = name_References_df['Subsection'].values[0]

    elif xsd_dict is not None:
        xs_element = xsd_dict.get('xs:element')
        xs = {}
        for d in xs_element:
            if d['@name'] == name:
                xs = d
                break
        if xs:
            Tags_dict[id]['Attributes']['Type'] = strDetached(xs.get('@type'))
            Tags_dict[id]['Labels']['Label'] = strDetached(xs.get('@name'))

    return id



""" LOOKUP TAGGER CLASS """
class LookupTagger():

    def __init__(self, resources):
        """
        This module uses the previousely filed xbrl report (html report with inline taxonomy tags) of the firm 
        along with Taxonomy resources to lookup and tag (label) the data in the desired html report. 

        resources: path of the folder containing the Taxonomy (XSD) files or "xlsx"
                If "xlsx", the excel version of the taxonomy data is downloaded and used. (Recomended)
                Otherwise, path of a folder contating the below files is required:
                    country-2020-01-31.xsd
                    dei-2020-01-31.xsd
                    srt-2020-01-31.xsd
                    srt-types-2020-01-31.xsd
                    us-gaap-2020-01-31.xsd
                    us-roles-2020-01-31.xsd
                    us-types-2020-01-31.xsd

        For more explanation and example please refer to "HTML Tagger documentation" and "test_HTML_tagger.ipynb"
        """

        self.resources = resources
        # If "resources" is "xlsx", the excel version of the Taxonomy data is doanloaded.
        if resources == 'xlsx':
            # Download the zip file contents in binary format
            url = 'https://www.fasb.org/cs/BlobServer?blobkey=id&blobnocache=true&blobwhere=1175836290847&blobheader=application%2Fzip&blobheadername2=Content-Length&blobheadername1=Content-Disposition&blobheadervalue2=9013838&blobheadervalue1=attachment%3B+filename%3DUS_GAAP_Taxonomy_2021.zip&blobcol=urldata&blobtable=MungoBlobs'
            r = requests.get(url)

            # Read the content of the zip file
            with ZipFile(BytesIO(r.content), 'r') as zipObj:
                file = zipObj.open(zipObj.namelist()[0])

            # Read required sheets
            Elements_df = pd.read_excel(file, sheet_name='Elements')
            pattern = '\[.*\]'
            Elements_df.loc[:, 'label'] = Elements_df['label'].str.replace(pattern, '').tolist()
            # Remove depricated taxonomy items
            self.Elements_df = Elements_df[Elements_df['deprecatedDate'].isna()]
            
            self.References_df = pd.read_excel(file, sheet_name='References', header=1)

            self.taxonomy = file

            print(f'Taxonomy excel file downloaded.')

        # If "resources" is a folder path, all .xsd files are returned a dict object containing all the data.
        else:
            # List all .xsd files
            all_files = glob.glob(self.resources + '/*.xsd')

            xsd_dict = {}
            # Read all file contents
            for f in all_files:
                xsd_f = xmlschema.XMLSchema(f)
                xsd_dict.update(xsd_f.to_dict(f))

            self.taxonomy = xsd_dict

            print(f'Taxonomy resources loaded from: {self.resources}')     


    def GetTags(self, html_FilePath, xbrl_FilePath, selected_facts=None):
        """
        Creates a lookup dict from tagged monetary data in tables and the firm specific facts in previously filed xbrl report, and US-GAAP Taxonomy resources. 
        Then the desired html report is scanned for the lookup data and the tags are returned.

        html_FilePath: file directory of the .html file to be tagged.
        xbrl_FilePath: file path of the previously filed xbrl report.
        selected_facts: list of fim specific fact for which the values from previously filed xbrl report is used for lookup.
        """

        # Create a lookup dictionary from previously filed xbrl report
        self.firmDict = firmDict(xbrl_FilePath, selected_facts)
        tables_dict = self.firmDict[0]
        firm_dict = self.firmDict[1]

        # Create a dict from taxonomy items not in the firmDict, from resources
        self.taxDict = {}
        if self.resources == 'xlsx':
            taxonomy_dict = dict(self.Elements_df[['label', 'name']].to_records(index=False))

            for item in taxonomy_dict:
                if taxonomy_dict[item] not in firm_dict.values():
                    self.taxDict[item] = taxonomy_dict[item]


        # Load the HTML file to be tagged
        self.parsed_html = LoadHTML(html_file = html_FilePath)

        # Search for the lookup dictionaries' items in the text data of HTML report
        Tags_dict = {}

        # First search tables for monetary data
        money_pattern = '\s*\(?(\d+(,\d+)+)\)?\s*' #pattern to match monetary values
        html_data = self.parsed_html.body.find_all()
        for elmnt in html_data:
            if elmnt.string:
                # Remove unicode strings and HTML characters
                string = remove_unicode(elmnt.string).strip()
                if string and (not string.isspace()):

                    # Find the best match for the text data in tables_dict
                    match = process.extractOne(string, tables_dict.keys(), scorer=fuzz.WRatio)
                    if match and (match[1] >= 95):
                        
                        name = tables_dict[match[0]]
                        id = get_tag_data(elmnt, Tags_dict, name, self.Elements_df, self.References_df)
                        fact = string
                        Tags_dict[id]['Attributes']['Fact'] = fact
                        
                        # Generate tag data for monetary values in tables
                        if elmnt.find_parent('tr'):
                            for st in elmnt.find_parent('tr'):
                                if (st.string) and (not st.string.isspace()):
                                    # Check if the fact is a monetary value
                                    if re.fullmatch(pattern=money_pattern, string=st.string):                                    
                                        id = get_tag_data(st, Tags_dict, name, self.Elements_df, self.References_df)

                                        # Save monetary value as numeric, not text
                                        fact = int(re.sub(pattern='\(|\)|,|\s', repl='', string=st.string))
                                        Tags_dict[id]['Attributes']['Fact'] = fact

                                        if st.string.startswith('('):
                                            sign = 'Negative'
                                        else:
                                            sign = 'Positive'
                                        Tags_dict[id]['Attributes']['Sign'] = sign
                        
                    else:
                        # Find the best match for the text data in firm_dict
                        match = process.extractOne(string, firm_dict.keys(), scorer=fuzz.WRatio)
                        if match and (match[1] >= 95):
                            name = firm_dict[match[0]]
                            id = get_tag_data(elmnt, Tags_dict, name, self.Elements_df, self.References_df)
                            fact = string
                            Tags_dict[id]['Attributes']['Fact'] = fact


        return Tags_dict