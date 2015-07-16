import commit_analysis as ca
import combine_output as co
import pandas as pd
import csv

def mapBug2Release(project, df):
    print 'Mapping bugs to releases ...'
    release_list = list()
    with open('../release_list/%s_releases.csv' %project, 'rb') as f:
        reader = csv.reader(f)
        for line in reader:
            release_list.append([line[1], line[0]])
    bug2release = list()
    
    for i, row in df.iterrows():        
        opened_date = str(row.opened_date)[:8]
        #   Take the lastest release before the bug opened date
        for r in release_list:
            if opened_date >= r[0]:
                bug2release.append(r[1])
                break
        #   If the bug's opened date is prior than the earlist release, then it's considered as a pre-release
        if opened_date < release_list[-1][0]:
            bug2release.append('pre_release')
    df['release'] = bug2release
    return df

def outputResults(df):
    print 'Outputing results ...'
    df.to_csv('results/%s_results.csv' %project, 
        columns=['bugID', 'opened_date', 'release', 'status', 'inheritance', 'overriding', 'fixed_date', 
        'modified_files'], 
        index=False)
    return

if(__name__ == '__main__'):
    project = 'rhino'
    temporary_results = False
    if project == 'mylyn' or project == 'jdtcore' or project == 'rhino':
          temporary_results = True
    cursor = ca.initDatabase(project)
    df_commits = ca.loadCommitLogs('../commit_logs/' + project + '_commits.txt')
    bug_dict, all_rev = ca.identifyAllBugFixes(df_commits, project, cursor)
    df_bugs = ca.hasKeywords(project, bug_dict, cursor, df_commits)
    df_bugs = ca.bugFixedDate(bug_dict, df_commits, df_bugs)
    df_bugs = ca.changedFiles('../commit_logs/' + project + '_files.txt', bug_dict, df_bugs)
    df_bugs = ca.bugReportMetrics(cursor, df_bugs)
    ca.outputResults(project, df_bugs, temporary_results)
    #   If combine the results from XML bug reports
    if temporary_results:
        df_commits = ca.loadCommitLogs('../commit_logs/' + project + '_commits.txt')
        df_xml_bugs = pd.read_csv('../bug_report_extract/results/' + project + '_results.csv')
        bug_set = set(df_xml_bugs['bugID'].values)
        bug_dict = co.mapBugToCommit(bug_set, df_commits)
        df_xml_bugs = ca.bugFixedDate(bug_dict, df_commits, df_xml_bugs)
        df_xml_bugs = ca.changedFiles('../commit_logs/' + project + '_files.txt', bug_dict, df_xml_bugs)
        df_bugs = co.combineAndOutput(project, df_xml_bugs)
    #   Map bugs to releases
    df_bugs = mapBug2Release(project, df_bugs)
    #   Output results
    outputResults(df_bugs)
    