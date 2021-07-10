from bs4 import BeautifulSoup
import xmlschema
import glob
import json
import os

# Function to filter html elements having "name" attribute
def has_name(tag):
    return tag.has_attr('name')

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

    def __init__(self, file, resources):
        """
        file: path of the HTML file to be tagged
        resources: path of the folder containing the Taxonomy (XSD) files
        """
        self.file = file
        self.resources = resources


    def LoadHTML(self, get_html=False):
        """
        Read the HTML file.
        Returns the parsed HTML object, if "get_html" is True.
        """
        with open(self.file, 'rb') as f:
            html_doc = f.read()

        parsed_html = BeautifulSoup(html_doc, 'html.parser')

        self.parsed_html = parsed_html
        if get_html:
            return parsed_html


    def LoadTaxonomy(self):
        """
        Read all Taxonomy files in .xsd format in the resources folder 
        Returns a dict object containing all the data
        """
        all_files = glob.glob(self.resources + '/*.xsd')

        xsd_dict = {}
        for f in all_files:
            xsd_f = xmlschema.XMLSchema(f)
            xsd_dict.update(xsd_f.to_dict(f))

        self.xsd_dict = xsd_dict
        #return xsd_dict


    def GetTags(self):
        """
        Tags the elements in the HTML file.
        Returns the dict of tagged id.
        """
        divs = self.parsed_html.body.find_all('div')
        xbrl_context = divs[0]
        xs_element = self.xsd_dict.get('xs:element')
        Tags_dict = {}

        for i in range(len(divs)):
            tags = divs[i].find_all(has_name)
            if tags:
                for tag in tags:
                    id = tag['id']
                    name = tag['name']
                    contextref = tag['contextref']

                    Tags_dict[id] = {'Attributes': {},
                                    'Labels': {},
                                    'References': {},
                                    'Calculation': {}}

                    xs = {}
                    for d in xs_element:
                        if d['@name'] == name.split(':')[-1]:
                            xs = d
                            break
                            
                    if tag.name == 'ix:nonfraction':
                        try:
                            fact = float(tag.string.replace(',', ''))
                        except:
                            fact = tag.string
                        try:
                            format = tag['format'].split(':')[-1]
                        except:
                            pass
                        try:
                            if tag['sign']=="-":
                                sign = 'Negative'
                        except:
                            sign = 'Positive'
                        try:
                            measure = tag['unitref']
                        except:
                            pass
                        try:
                            scale = tag['scale']
                        except:
                            pass
                        
                        Tags_dict[id]['Attributes']['Format'] = format
                        Tags_dict[id]['Attributes']['Measure'] = measure
                        Tags_dict[id]['Attributes']['Scale'] = scale
                        Tags_dict[id]['Attributes']['Sign'] = sign

                    else:
                        fact = tag.string

                    Tags_dict[id]['Attributes']['Tag'] = name
                    Tags_dict[id]['Attributes']['Fact'] = fact

                    try:
                        start = xbrl_context.find_all(id=contextref)[0].find('xbrli:startdate').text
                        end = xbrl_context.find_all(id=contextref)[0].find('xbrli:startdate').text
                        Tags_dict[id]['Attributes']['Period'] = start + ' to ' + end
                    except:
                        date = xbrl_context.find_all(id=contextref)[0].find('xbrli:instant').text
                        Tags_dict[id]['Attributes']['Period'] = 'As of ' + end

                    if xs:
                        Tags_dict[id]['Attributes']['Type'] = strDetached(xs.get('@type'))

                        Tags_dict[id]['Labels']['Label'] = strDetached(xs.get('@name'))

        return Tags_dict
        