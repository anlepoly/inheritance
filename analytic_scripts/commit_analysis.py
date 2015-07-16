import csv, re
import MySQLdb
import pandas as pd

# initialise the MySQL service
def initDatabase(project):
    if project == 'rhino':
        db_name = 'Mozilla_Bugzilla'
    elif project == 'mylyn' or project == 'jdtcore':
        db_name = 'Eclipse_Bugzilla'
    #   Please set the database host, user and password here
    database = MySQLdb.connect(host = 'localhost', user = 'root', passwd = 'your_passwd', db = dbname, port = 3306)
    cursor = database.cursor()
    return cursor

#   Load all commit logs
def loadCommitLogs(filename):
    print 'Loading all commit logs from Mozilla VCS ...'
    with open(filename, 'rb') as f:
        reader = f.read()
    log_list = list()
    for line in reader.split('\n'):
        if len(line):
            if line[0] != ' ':
                seg_list = line.split(', ')
                if len(seg_list) > 4:
                    seg_list[3] = ', '.join(seg_list[3:])
                log_list.append(seg_list[:4])
    df = pd.DataFrame(log_list, columns=['revision', 'author', 'date', 'message'])
    return df

#   Identify bug fixes for each crash-related bug
def identifyAllBugFixes(df, project, cursor):
    print 'Identifying all bug fixes in the history ...'
    bug_dict = dict()
    all_rev = set()
    row_iterator = df.iterrows()
    pattern = r'(?:bug|bug|bugzilla|b=|bg|issue|id=|#)[s\s\-#]?([1-9][0-9]+)'
    if project == 'mylyn':
        pattern = r'([1-9][0-9]{4,})\:'
    for i, row in row_iterator:
        rev_hash = row['revision']
        commit_message = row['message']
        number_list = re.findall(pattern, commit_message, re.IGNORECASE)
        for a_number in number_list:
            cursor.execute('SELECT bug_id FROM bugs WHERE bug_id = ' + a_number)
            if len(cursor.fetchall()):
                #print commit_message
                #print '+'*100
                bugID = int(a_number)
                all_rev.add(rev_hash)
                #   the fixes of each bug
                if bugID in bug_dict:
                    rev_set = bug_dict[bugID]
                    rev_set.add(rev_hash)
                else:
                    bug_dict[bugID] = set([rev_hash])
            else:
                print a_number
    print 'Number of bugs that have fixes detected:', len(bug_dict)
    return bug_dict, all_rev

def writeDetailToFiles(project, target, output_text, bugID):
    with open('results/text_with_keywords/' + project + '/' + target + '/' + str(bugID) + '.txt', 'wb') as f:
        f.write(output_text)
    return

def matchKeywords(project, target, title, comments, rev_set, rev_message_dict, bugID):
    matched = False
    output_text = ''
    if target == 'inheritance':
        pattern = r'super[\s\-]?class|base[\s\-]?class|sub[\s\-]?class|inherit|polymorphism|hierach|exten(d|sion)'
    elif target == 'overriding':
        pattern = r'overrid'
    #   Match keywords from the bug report' title and comments
    if re.search(pattern, title):
        matched = True
        output_text += ('BUG TITLE:\n%s\n\n' %title)
        #return 'YES'
    if re.search(pattern, comments):
        matched = True
        output_text += ('BUG REPORT COMMENTS:\n%s\n\n' %comments)
        #return 'YES'
    #   Match keywords from the bug related bug fixes
    '''commit_message = ''
    for rev_hash in rev_set:
        if re.search(pattern, rev_message_dict[rev_hash]):
            matched = True
            commit_message += (rev_message_dict[rev_hash] + '\n')
    if len(commit_message):
        output_text += ('COMMIT MESSAGES:\n%s\n\n' %commit_message)
            #return 'YES' '''
    if matched:
        writeDetailToFiles(project, target, output_text, bugID)
        #print output_text
        return 'YES'
    return 'NO'

def hasKeywords(project, bug_dict, cursor, df_commits):
    print 'Identify keywords in bug reports and commit messages ...'
    rev_message_dict = df_commits[['revision', 'message']].set_index('revision').to_dict()['message']
    bug_list = list()     
    for bugID in bug_dict:
        title, comments = '', ''
        cursor.execute('SELECT short_desc FROM bugs WHERE bug_id = ' + str(bugID))
        results = cursor.fetchall()
        title = results[0][0]
        cursor.execute('SELECT comments FROM bugs_fulltext where bug_id = ' + str(bugID))
        results = cursor.fetchall()
        comments = results[0][0]
        commit_messages = bug_dict[bugID]
        inheritance = matchKeywords(project, 'inheritance', title, comments, bug_dict[bugID], rev_message_dict, bugID)
        overriding = matchKeywords(project, 'overriding', title, comments, bug_dict[bugID], rev_message_dict, bugID)
        bug_list.append([bugID, inheritance, overriding])
    df_bugs = pd.DataFrame(bug_list, columns=['bugID', 'inheritance', 'overriding']).sort('bugID')
    return df_bugs

def bugFixedDate(bug_dict, df_commits, df_bugs):
    print 'Extract commit date of bug fixes ...'
    rev_date_dict = df_commits[['revision', 'date']].set_index('revision').to_dict()['date']
    date_list = list()
    for bugID in df_bugs['bugID'].values:
        rev_set = bug_dict[bugID]
        date_set = set()
        for rev_hash in rev_set:
            fixed_date = rev_date_dict[rev_hash]
            date_str = pd.to_datetime(fixed_date[:-6], format='%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M%S')
            date_set.add(date_str)
        date_list.append(' '.join(sorted(date_set)))
    df_bugs['fixed_date'] = date_list
    return df_bugs

def addChangedFile2Dict(file_dict, line, last_rev):
    changed_file = line.split('\t')[1].strip()
    if last_rev in file_dict:
        file_dict[last_rev].add(changed_file)
    else:
        file_dict[last_rev] = set([changed_file])
    return

def changedFiles(filename, bug_dict, df_bugs):
    print "Identify revisions' modified files  ..."
    mod_file_dict = dict()
    add_file_dict = dict()
    del_file_dict = dict()
    with open(filename, 'rb') as f:
        reader = f.read()
    last_rev = None
    for line in reader.split('\n'):
        if line.startswith('commit'):
            last_rev = line.split(' ')[1].strip()
        elif len(line):
            if line[0] == 'M':
                addChangedFile2Dict(mod_file_dict, line, last_rev)
            elif line[0] == 'A':
                addChangedFile2Dict(add_file_dict, line, last_rev)
            elif line[0] == 'D':
                addChangedFile2Dict(del_file_dict, line, last_rev) 
    print 'Mapping modified files to their bugs ...' 
    mod_file_list = list()
    add_file_list = list()
    del_file_list = list()
    for bugID in df_bugs['bugID'].values:
        rev_set = bug_dict[bugID]
        mod_files = set()
        add_files = set()
        del_files = set()
        for rev_hash in rev_set:
            if rev_hash in mod_file_dict:
                mod_files |= mod_file_dict[rev_hash]
            if rev_hash in add_file_dict:
                add_files |= add_file_dict[rev_hash]
            if rev_hash in del_file_dict:
                del_files |= del_file_dict[rev_hash]
        mod_file_list.append(' '.join(sorted(mod_files)))
        add_file_list.append(' '.join(sorted(add_files)))
        del_file_list.append(' '.join(sorted(del_files)))
    df_bugs['modified_files'] = mod_file_list
    df_bugs['added_files'] = add_file_list
    df_bugs['deleted_files'] = del_file_list
    return df_bugs

def bugReportMetrics(cursor, df_bugs):
    print 'Extract bug opened date and status ...'
    opened_list = list()
    status_list = list()
#    version_list = list()
    for bugID in df_bugs['bugID'].values:
        cursor.execute('SELECT creation_ts, bug_status, version FROM bugs WHERE bug_id = ' + str(bugID))
        results = cursor.fetchall()
        opened_list.append(results[0][0].strftime('%Y%m%d%H%M%S'))
        status_list.append(results[0][1])
#        version_list.append(results[0][2])
    df_bugs['opened_date'] = opened_list
    df_bugs['status'] = status_list
#    df_bugs['release'] = version_list
    return df_bugs

def outputResults(project, df_bugs, temporary_results):
    if temporary_results == True:
        folder = 'temporary/'
    else:
        folder = 'results/'
    df_bugs.to_csv(folder + project + '_results.csv', 
        columns=['bugID', 'opened_date', 'status', 'inheritance', 'overriding', 'fixed_date', 'modified_files', 'added_files', 'deleted_files'], 
        index=False)
    return
    
if(__name__ == '__main__'):
    project = 'rhino'
    temporary_results = False
    if project == 'mylyn' or project == 'jdtcore':
          temporary_results = True
    cursor = initDatabase(project)
    df_commits = loadCommitLogs('../commit_logs/' + project + '_commits.txt')
    bug_dict, all_rev = identifyAllBugFixes(df_commits, project, cursor)
    df_bugs = hasKeywords(project, bug_dict, cursor, df_commits)
    df_bugs = bugFixedDate(bug_dict, df_commits, df_bugs)
    df_bugs = changedFiles('../commit_logs/' + project + '_files.txt', bug_dict, df_bugs)
    df_bugs = bugReportMetrics(cursor, df_bugs)
    outputResults(project, df_bugs, temporary_results)
    #print all_rev
    