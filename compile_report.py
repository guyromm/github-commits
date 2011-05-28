#!/usr/bin/python

import json,glob,os,datetime,re,sys
import dateutil.parser
from commands import getstatusoutput as gso
usermap = {re.compile('milez'):'guyromm@gmail.com'
           ,re.compile(re.escape('3demax@ukr.net')):'3demax@gmail.com'
           ,re.compile(re.escape('dima@dima-Latitude-D820.')):'maltsev.dima7@gmail.com'
           }
GITHUB_USER = open('githubuser.txt','r').read().strip()
GITHUB_PASSWORD = open('githubpw.txt','r').read().strip()
GITHUB_PROJECTS = open('githubprojects.txt','r').read().strip().split('\n')

by_user={}
by_project={}
by_date={}

user_project={}
user_date={}
user_project_date={}

for proj in GITHUB_PROJECTS:
    ofn = os.path.join('data','%s.json'%proj)
    if not os.path.exists(ofn):
        print 'fetching project %s'%proj
        cmd = "curl -u '%s' 'http://github.com/api/v2/json/commits/list/%s/%s/master' > data/%s.json"%(GITHUB_PASSWORD,GITHUB_USER,proj,proj)
        st,op=gso(cmd) ; assert st==0
    else:
        print 'already got %s'%proj

def initarr():
    return {'times':0,'diff':0,'removed':0,'added':0,'ids':[]}

if len(sys.argv)>1:
    fr,to = [datetime.datetime.strptime(it,'%Y-%m-%d').date() for it in sys.argv[1].split(':')]
else:
    fr,to = None,None
comre = re.compile('([a-f0-9]{16})')
for fn in glob.glob('data/*.json'):
    if comre.search(fn): continue
    obj = json.loads(open(fn,'r').read())

    print 'going over proj %s'%fn
    assert 'commits' in obj,'cannot find commits in %s'%fn
    for c in obj['commits']:
        projfn = os.path.basename(fn).replace('.json','')

        comfn = os.path.join('data','%s.%s.json'%(projfn,c['id']))

        user = c['committer']['email']
        for um,uv in usermap.items():
            if um.search(user):
                user = uv
                break
        assert user,c
        proj = os.path.basename(fn).replace('.json','')
        date = dateutil.parser.parse(c['authored_date'])
        if fr and date.date()<fr: continue
        if to and date.date()>to: continue
        print '%s -> %s on %s'%(user,proj,date)
        comid = '/%s/%s/commit/%s'%(GITHUB_USER,projfn,c['id'])
        commsg = c['message']
        if not os.path.exists(comfn):
            print 'fetching commit'
            comurl = 'http://github.com/api/v2/json/commits/show/%s/%s/%s'%(GITHUB_USER,projfn,c['id'])
            curlcmd = 'curl -u %s %s > %s'%(GITHUB_PASSWORD,comurl,comfn)
            st,op = gso(curlcmd) ; assert st==0
            assert os.path.exists(comfn)
        try:
            comdt = json.loads(open(comfn).read())
        except:
            raise Exception('could not load from %s'%comfn)
        if 'modified' in comdt['commit']:
            try:
                dfsum = sum([len(mod['diff'].split('\n')) for mod in comdt['commit']['modified'] if 'diff' in mod])
            except:
                raise Exception(comdt['commit']['modified'])
        else:
            dfsum =0

        if 'removed' in comdt['commit']:
            removed = len(comdt['commit']['removed'])
        else:
            removed = 0

        if 'added' in comdt['commit']:
            added = len(comdt['commit']['added'])
        else:
            added = 0

        if user not in by_user: 
            user_project_date[user]={}
            user_date[user]={}
            user_project[user]={}
            by_user[user]=initarr()
            
        def incr(o):
            global dfsum,added,removed,comid,commsg
            o['times']+=1
            o['diff']+=dfsum
            o['removed']+=removed
            o['added']+=added
            o['ids'].append([comid,commsg])
        
        incr(by_user[user])

        if proj not in by_project: 
            by_project[proj]=initarr()

        if proj not in user_project[user]:
            user_project[user][proj]=initarr()

        incr(user_project[user][proj])
        incr(by_project[proj])

        if date.date() not in by_date: 
            by_date[date.date()]=initarr()

        if date.date() not in user_date[user]:
            user_date[user][date.date()]=initarr()

        if proj not in user_project_date[user]: user_project_date[user][proj]={}
        if date.date() not in user_project_date[user][proj]: user_project_date[user][proj][date.date()]=initarr()

        incr(user_project_date[user][proj][date.date()])
        incr(by_date[date.date()])
        incr(user_date[user][date.date()])

op="""<doctype !html>
<html>
<head>
<style type='text/css'>
thead { background-color:#abc; }
</style>
</head>
<body>
"""
dtpat = "<table><thead><tr><th>date<th>commits<th>added<th>removed<th>difflines<th>links</tr></thead><tbody>\n"
dtendpat = "</tbody></table>"
rowpat = "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n"
def mkrow(date,dt,commits=True):
    if commits:
        cm = ', '.join(["<a href='https://github.com/%s' title='%s'>%s</a>"%(com,commsg,com.split('/')[4][0:4]) for com,commsg in dt['ids']])
    else:
        cm=''
    rt= rowpat%(date,dt['times'],dt['added'],dt['removed'],dt['diff'],cm)
    return rt
def srtit(a1,a2):
    return cmp(a1[0],a2[0])
def srt2(i1,i2):
    return cmp(i1[1]['diff'],i2[1]['diff'])

if fr:op+="<small>commits are starting from %s</small><br />"%(fr)
if to:op+="<small>commits are until %s</small></br >"%(to)
op+="<h1>user totals</h1>"
op+=dtpat
uitems = by_user.items()
uitems.sort(srt2,reverse=True)
for user,commits in uitems:
    op+=mkrow(user,commits,commits=False)
op+=dtendpat
for user,projects in user_project_date.items():
    op+="<h1>%s commits by %s into %s project(s)</h1>\n"%(by_user[user]['times'],user,len(user_project[user]))

    op+="<h2>by dates</h2>\n"
    dates = user_date[user].items()
    dates.sort(srtit)
    op+=dtpat
    for date,commits in dates:
        op+=mkrow(date,commits,commits=True)
    op+="</tbody></table>"

    for proj,dates in projects.items():
        op+="<h3>into project %s</h3>"%proj
        commits = dates.items()
        commits.sort(srtit)
        op+=dtpat
        for date,commits in commits:
            op+=mkrow(date,commits)
        op+="</tbody></table>"
op+="</body></html>"
ofn = 'commits'
if fr: ofn+='-%s'%fr
if to: ofn+=':%s'%to
ofn+='.html'
fp = open(ofn,'w') ; fp.write(op) ; fp.close()
print 'written to %s'%ofn

