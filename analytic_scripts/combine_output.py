import re
import commit_analysis as ca
import pandas as pd

def mapBugToCommit(bug_set, df_commits):
    bug_dict = dict()
    for rev_hash, msg in df_commits[['revision', 'message']].values:
        bug_list = re.findall(r'[0-9]+', msg)
        for a_number in bug_list:
            bugID = int(a_number)
            if bugID in bug_set:
                if bugID in bug_dict:
                    bug_dict[bugID].add(rev_hash)
                else:
                    bug_dict[bugID] = set([rev_hash])
    print 'Number of bugs that have fixes detected:', len(bug_dict)
    return bug_dict

def combineAndOutput(project, df_bugs):
    df_temp = pd.read_csv('temporary/' + project + '_results.csv')
    return pd.concat([df_temp, df_bugs])

if __name__ == '__main__':
    project = 'mylyn'
    df_commits = ca.loadCommitLogs('../commit_logs/' + project + '_commits.txt')
    df_bugs = pd.read_csv('../bug_report_extract/results/' + project + '_results.csv')
    bug_set = set(df_bugs['bugID'].values)
    bug_dict = mapBugToCommit(bug_set, df_commits)
    df_bugs = ca.bugFixedDate(bug_dict, df_commits, df_bugs)
    df_bugs = ca.changedFiles('../commit_logs/' + project + '_files.txt', bug_dict, df_bugs)
    combineAndOutput(project, df_bugs)
    