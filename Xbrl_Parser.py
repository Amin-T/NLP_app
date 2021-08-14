from xbrl.cache import HttpCache
from xbrl.instance import XbrlParser, XbrlInstance

cache = HttpCache('./cache')
xbrlParser = XbrlParser(cache)

def read_xbrl(file_path, selected_facts = None, non_dimensional = False):
    """
    This function parses a xbrl file and returns a list of dict objects.

        file_path: path to the .htm file.
        selected_facts: facts to be extracted from the xbrl file.
        non_dimensional: only select non-dimensional data.
    """

    ixbrl_path = file_path
    inst = xbrlParser.parse_instance_locally(ixbrl_path)

    extracted_data = {}
    for fact in inst.facts:
        if selected_facts:
            if fact.concept.name not in selected_facts: 
                continue
        if non_dimensional:
            if len(fact.context.segments) > 0: 
                continue

        extracted_data[fact.concept.name] = {'type': fact.concept.type}
        
    return extracted_data

