from bs4 import BeautifulSoup
import xmlschema
import glob
from zipfile import ZipFile
from io import BytesIO
import requests
import pandas as pd

# Function to filter html elements having "name" attribute
def has_name(tag):
    return tag.has_attr('name')

# Function to filter html elements having "name" and "id" attributes
def has_name_id(tag):
    return tag.has_attr('name') and (tag.has_attr('contextref') or tag.has_attr('id'))

# Function to detache strings
def strDetached(string, split=True, split_by=':'):
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


class HTMLtagger():

    def __init__(self, resources):
        """
        resources: path of the folder containing the Taxonomy (XSD) files
                    or "xlsx"
                If resources = "xlsx", the excel version of the taxonomy data 
                will be downloaded and used.
        """

        self.resources = resources


    def LoadHTML(self, file, get_html=False):
        """
        Read the HTML file.
        Returns the parsed HTML object, if "get_html" is True.
        """
        with open(file, 'rb') as f:
            html_doc = f.read()

        parsed_html = BeautifulSoup(html_doc, 'html.parser')

        self.parsed_html = parsed_html
        if get_html:
            return parsed_html


    def LoadTaxonomy(self):
        """
        If "resources" is a folder path, read all Taxonomy files in .xsd format in the
        resources folder and returns a dict object containing all the data.

        If "resources" is "xlsx", the excel version of the Taxonomy data is doanloaded and 
        returns a binary object of the excel file.
        """
        if self.resources == 'xlsx':
            # Download the zip file contents in binary format
            url = 'https://www.fasb.org/cs/BlobServer?blobkey=id&blobnocache=true&blobwhere=1175836290847&blobheader=application%2Fzip&blobheadername2=Content-Length&blobheadername1=Content-Disposition&blobheadervalue2=9013838&blobheadervalue1=attachment%3B+filename%3DUS_GAAP_Taxonomy_2021.zip&blobcol=urldata&blobtable=MungoBlobs'
            r = requests.get(url)

            # Read the content of the zip file
            with ZipFile(BytesIO(r.content), 'r') as zipObj:
                file = zipObj.open(zipObj.namelist()[0])

            self.taxonomy = file
        
        else:
            all_files = glob.glob(self.resources + '/*.xsd')

            xsd_dict = {}
            for f in all_files:
                xsd_f = xmlschema.XMLSchema(f)
                xsd_dict.update(xsd_f.to_dict(f))

            self.taxonomy = xsd_dict

        #return xsd_dict


    def GetTags(self):
        """
        Tags the elements in the HTML file.
        Returns the dict of tagged id.
        """
        tags = self.parsed_html.body.find_all(has_name_id)
        xbrl_context = self.parsed_html.body.find('ix:header')
        Tags_dict = {}

        if self.resources == 'xlsx':
            Elements_df = pd.read_excel(self.taxonomy, sheet_name='Elements')
            References_df = pd.read_excel(self.taxonomy, sheet_name='References', header=1)
        else:
            xs_element = self.taxonomy.get('xs:element')

        for tag in tags:
            name = tag['name']
            contextref = tag['contextref']
            if tag.has_attr('id'):
                id = tag['id']
            else:
                id = name + contextref

            Tags_dict[id] = {'Attributes': {},
                            'Labels': {},
                            'References': {},
                            'Calculation': {}}
                    
            if tag.name == 'ix:nonfraction':
                try:
                    fact = float(tag.string.replace(',', ''))
                except:
                    fact = tag.string

                try:
                    format = tag['format'].split(':')[-1]
                    Tags_dict[id]['Attributes']['Format'] = format
                except:
                    pass
                
                try:
                    if tag['sign']=="-":
                        sign = 'Negative'
                except:
                    sign = 'Positive'
                Tags_dict[id]['Attributes']['Sign'] = sign

                try:
                    measure = tag['unitref']
                    Tags_dict[id]['Attributes']['Measure'] = measure
                except:
                    pass

                try:
                    scale = tag['scale']
                    Tags_dict[id]['Attributes']['Scale'] = scale
                except:
                    pass
                
            else:
                fact = tag.string

            Tags_dict[id]['Attributes']['Tag'] = name
            Tags_dict[id]['Attributes']['Fact'] = fact

            start = ''
            end = ''
            date = ''
            try:
                start = xbrl_context.find(id=contextref).find('xbrli:startdate').text
                end = xbrl_context.find(id=contextref).find('xbrli:startdate').text
                Tags_dict[id]['Attributes']['Period'] = start + ' to ' + end
            except:
                try:
                    date = xbrl_context.find(id=contextref).find('xbrli:instant').text
                    Tags_dict[id]['Attributes']['Period'] = 'As of ' + date
                except:
                    pass
            
            if self.resources == 'xlsx':
                name_Elements_df = Elements_df[Elements_df['name'] == name.split(':')[-1]]
                if not name_Elements_df.empty:
                    Tags_dict[id]['Attributes']['Type'] = name_Elements_df['type'].values[0].split(':')[-1]
                    Tags_dict[id]['Labels']['Documentation'] = name_Elements_df['documentation'].values[0]
                    Tags_dict[id]['Labels']['Label'] = name_Elements_df['label'].values[0]

                name_References_df = References_df[References_df['name'] == name.split(':')[-1]]
                if not name_References_df.empty:
                    Tags_dict[id]['References']['Name'] = name_References_df['Name'].values[0]
                    Tags_dict[id]['References']['Number'] = name_References_df['Number'].values[0]
                    Tags_dict[id]['References']['Publisher'] = name_References_df['Publisher'].values[0]
                    Tags_dict[id]['References']['Section'] = name_References_df['Section'].values[0]
                    Tags_dict[id]['References']['Subsection'] = name_References_df['Subsection'].values[0]
            else:
                xs = {}
                for d in xs_element:
                    if d['@name'] == name.split(':')[-1]:
                        xs = d
                        break
                if xs:
                    Tags_dict[id]['Attributes']['Type'] = strDetached(xs.get('@type'))
                    Tags_dict[id]['Labels']['Label'] = strDetached(xs.get('@name'))

        return Tags_dict

