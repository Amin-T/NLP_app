# Financial reports tagger

The purpose of this project is to take financial documents, which are prepared in accordance to the US-GAAP accounting standard, in .html or pdf formats as input,
extract financial elements and entities from the text and provide tags in the document as output. The "tagger" consists of 2 separate modules:
* HTML tagger
* NER tagger

Import the tagger as:

```
from HTML_tagger import HTMLtagger
```

