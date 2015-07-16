import os, csv, re
from datetime import datetime
import xml.etree.ElementTree as ET

def matchKeywords(target, description):
    if target == 'inheritance':
        pattern = r'super[\s\-]?class|base[\s\-]?class|sub[\s\-]?class|inherit|polymorphism|hierach|exten(d|sion)'
    elif target == 'overriding':
        pattern = r'overrid'
    if re.search(pattern, description):
        return 'YES'
    return 'NO'

def hasKeywords(description, pos):
    inheritance = matchKeywords('inheritance', description)
    overriding = matchKeywords('overriding', description)
    return (inheritance, overriding)

def parseXMLReport(filename):
    bugID = filename.split('.')[0]
    result_list = list()
    tree = ET.parse('bug_reports/' + project + '/' + filename)
    root = tree.getroot()
    opened_date = ''
    # Bug opened time
    for elem in tree.iter('creation_ts'):
        opened_date = datetime.strptime(elem.text[:-6], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M%S')
    if len(opened_date) == 0:
        return None
    # Bug status
    for elem in tree.iter('bug_status'):
        status = elem.text
    
    inheritance_text, overriding_text = '', ''
    inheritance_comments, overriding_comments = '', ''
    # Keywords
    for elem in tree.iter('short_desc'):
        inheritance, overriding = hasKeywords(elem.text, 'title')
    
    if inheritance == 'YES':
        inheritance_text += ('BUG TITLE:\n%s\n\n' %elem.text)
    if overriding == 'YES':
        overriding_text += ('BUG TITLE:\n%s\n\n' %elem.text)    
    #if inheritance == 'NO' or overriding == 'NO':
    for elem in tree.iter('thetext'):
        if elem.text:
            inheritance, overriding = hasKeywords(elem.text, 'comments')
            if inheritance == 'YES':
                inheritance_comments += (elem.text + '\n')
            if overriding == 'YES':
                overriding_comments += (elem.text + '\n')
                #break
    if len(inheritance_comments):
        inheritance_text += ('BUG REPORT COMMENTS:\n%s\n\n' %elem.text)
    if len(overriding_comments):
        overriding_text += ('BUG REPORT COMMENTS:\n%s\n\n' %elem.text) 
    
    if len(inheritance_text):
        #print inheritance_text
        with open('results/text_with_keywords/' + project + '/inheritance/' + bugID + '.txt', 'wb') as f:
            f.write(inheritance_text)
    if len(overriding_text):
        #print overriding_text
        with open('results/text_with_keywords/' + project + '/overriding/' + bugID + '.txt', 'wb') as f:
            f.write(overriding_text)
    
    return [bugID, opened_date, status, inheritance, overriding]

if __name__ == '__main__':
    project = 'rhino'
    csv_writer = csv.writer(open('results/' + project + '_results.csv', 'wb'))
    csv_writer.writerow(['bugID', 'opened_date', 'status', 'inheritance', 'overriding'])
    file_list = sorted(os.listdir('bug_reports/' + project))
    for f in file_list:
        if f.endswith('.xml'):
            print f
            result_list = parseXMLReport(f)
            if result_list:
                csv_writer.writerow(result_list)
