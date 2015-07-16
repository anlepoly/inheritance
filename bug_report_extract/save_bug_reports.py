import urllib2

def downloadReport(bugID, project):
    #   Initialise variables
    url = 'https://bugs.eclipse.org/bugs/show_bug.cgi?ctype=xml&id=' + bugID
    
    urlItem = None
    #   download bug reports as xml
    try:
        urlItem = urllib2.urlopen(url)
    except:
        print 'Invalid bug ID or non-authorised access'
    if(urlItem):
        pageBytes = urlItem.read()
        pageTxt = pageBytes.decode('utf-8', 'ignore')
        xmlStr = pageTxt.encode('ascii','ignore')        
        with open('bug_reports/' + project + '/' + bugID + '.xml', 'wb') as f:
            f.write(xmlStr)
    return
    
if(__name__ == '__main__'):
    project = 'jdtcore'
    with open(project + '_bugs.txt', 'rb') as f:
        read_data = f.read()
    for bugID in read_data.split('\n'):
        print bugID
        downloadReport(bugID, project)
