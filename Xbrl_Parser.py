from xbrl.cache import HttpCache
from xbrl.instance import XbrlParser

cache = HttpCache('./cache')
xbrlParser = XbrlParser(cache)

def read_xbrl(file_path, selected_facts = None, values = True, non_dimensional = False):
    """
    This function uses Python's py-xbrl library to parse a xbrl file and returns a dict object of extracted data.

        file_path: path to the .htm (xbrl) file.
            > file directory files
        selected_facts: facts (taxonomy tag names) to be extracted from the xbrl file.
            > list of names
        values: whether or not the values of the extracted facts to be returned.
            > True will return vales, False otherwise.
        non_dimensional: only select non-dimensional data.

    For more explanation and example please refer to "HTML Tagger documentation" and "test_HTML_tagger.ipynb"
    """

    # Initialize the parser
    inst = xbrlParser.parse_instance_locally(file_path)

    extracted_data = {}

    for fact in inst.facts:

        if selected_facts:
            # Check if the fact name is in the list of selected facts
            if fact.concept.name not in selected_facts: 
                continue

        if non_dimensional:
            if len(fact.context.segments) > 0: 
                continue
    
        if values:
            extracted_data[fact.concept.name] = {
                'label': fact.concept.labels[-1].text,
                'value': fact.value
            }
        else:
            extracted_data[fact.concept.name] = {'type': fact.concept.type}
        
    return extracted_data

