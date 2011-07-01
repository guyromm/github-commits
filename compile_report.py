#!/usr/bin/python

import json,glob,os,datetime,re,sys
from commands import getstatusoutput as gso
usermap = {re.compile('milez'):'guyromm@gmail.com'
           ,re.compile(re.escape('3demax@ukr.net')):'3demax@gmail.com'
           ,re.compile(re.escape('dima@dima-Latitude-D820.')):'maltsev.dima7@gmail.com'
           ,re.compile(re.escape('nskrypnik@hosted-by.leaseweb.com')):'nskrypnik@gmail.com'
           ,re.compile(re.escape('Den@.(none)')):'mr.dantsev@gmail.com'
           }
GITHUB_USER = open('githubuser.txt','r').read().strip()
GITHUB_PASSWORD = open('githubpw.txt','r').read().strip()
GITHUB_PROJECTS = open('githubprojects.txt','r').read().strip().split('\n')

by_user={}
by_project={}

by_date={}

user_project={}
project_user={}
user_date={}
user_project_date={}
project_date={}

for proj in GITHUB_PROJECTS:
    ofn = os.path.join('data','%s.json'%proj)
    fetchnew=True

    if os.path.exists(ofn):
        st = os.stat(ofn)
        fmt = datetime.datetime.fromtimestamp(st.st_mtime)
        oneh = (datetime.datetime.now()-datetime.timedelta(days=1))
        #print 'fmt = %s; oneh = %s'%(fmt,oneh)
        if fmt>=oneh:
            fetchnew=False
        else:
            os.unlink(ofn)
    if fetchnew:
        print 'fetching project %s'%proj
        pagenum=1
        wr={'commits':[]}
        while True:
            print 'taking page %s'%pagenum
            cmd = "curl -s -u '%s' 'http://github.com/api/v2/json/commits/list/%s/%s/master?page=%s'"%(GITHUB_PASSWORD,GITHUB_USER,proj,pagenum)
            st,op=gso(cmd) ; assert st==0
            pagenum+=1
            dt = json.loads(op)
            if 'commits' in dt: print '%s entries'%len(dt['commits'])
            if 'commits' not in dt or not len(dt['commits']): break
            wr['commits']+=dt['commits']

        fp = open(ofn,'w') ; fp.write(json.dumps(wr)); fp.close()
            
    else:
        print '%s is recent enough'%proj

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
        date = datetime.datetime.strptime(c['authored_date'][0:-5],'%Y-%m-%dT%H:%M:%S-') #dateutil.parser.parse(c['authored_date'])

        if fr and date.date()<fr: continue
        if to and date.date()>to: continue
        #print '%s -> %s on %s'%(user,proj,date)
        comid = '/%s/%s/commit/%s'%(GITHUB_USER,projfn,c['id'])
        commsg = c['message']
        if not os.path.exists(comfn):
            print 'fetching commit %s'%c['id']
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

        if proj not in project_date: project_date[proj]={}
        if proj not in project_user: project_user[proj]={}
        if user not in project_user[proj]: project_user[proj][user]=initarr()
        if date.date() not in project_date[proj]: project_date[proj][date.date()] = initarr()
        
        if user not in by_user: 
            user_project_date[user]={}
            user_date[user]={}
            user_project[user]={}
            by_user[user]=initarr()
        def idsort(i1,i2):
            return cmp(i1[3],i2[3])
        def incr(o):
            global dfsum,added,removed,comid,commsg
            o['times']+=1
            o['diff']+=dfsum
            o['removed']+=removed
            o['added']+=added
            o['ids'].append([comid,commsg,user,date])
            o['ids'].sort(idsort)
        incr(by_user[user])
        incr(project_user[proj][user])
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

        incr(project_date[proj][date.date()])
        incr(user_project_date[user][proj][date.date()])
        incr(by_date[date.date()])
        incr(user_date[user][date.date()])

def srtit(a1,a2):
    return cmp(a1[0],a2[0])
def srt2(i1,i2):
    return cmp(i1[1]['diff'],i2[1]['diff'])
def srt3(i1,i2):
    return cmp(i1[0],i2[0])
import time
def totimestamp(dt):
    return time.mktime(dt.timetuple()) + 0/1e6 #dt.microsecond/1e6
        
jsexp=[]
for user in user_date:
    items = user_date[user].items()

    #print([totimestamp(it[0]) for it in items])
    for item in items:
        #if user not in ['nskrypnik@gmail.com','3demax@gmail.com']: continue #'3demax@gmail.com': continue
        tm = int(totimestamp(item[0]))
        curi = item[1]['diff']
        jsexp.append({'action':user,'time':curi,'curitems':int(tm)})
def srtjsexp(i1,i2):
    return cmp(i1['curitems'],i2['curitems'])

jsexp.sort(srtjsexp)

op="""<doctype !html>
<html>
<head>
<script type='text/javascript' src='jquery-1.6.1.min.js'></script>
<script type='text/javascript' src='raphael-min.js'></script>
<script type='text/javascript'>
var data = %s;
</script>
<script type='text/javascript' src='plotgraph.js'></script>
<style type='text/css'>
#info { width:920px; height:200px; }
thead { background-color:#abc; }
</style>
</head>
<body>
<div id='info'></div>
"""%(json.dumps(jsexp))

dtpat = "<table><thead><tr><th>date<th>commits<th>added<th>removed<th>difflines<th>links</tr></thead><tbody>\n"
dtendpat = "</tbody></table>"
rowpat = "<tr><td><nobr>%s</nobr></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n"
def mkrow(date,dt,commits=True):
    if commits:
        cm = ', '.join(["<a href='https://github.com%s' title='%s by %s on %s'>%s</a>"%(com,commsg,user,stamp,com.split('/')[4][0:4]) for com,commsg,user,stamp in dt['ids']])
    else:
        cm=''
    rt= rowpat%(date,dt['times'],dt['added'],dt['removed'],dt['diff'],cm)
    return rt
opa=[]
if fr:opa.append("commits are starting from %s"%(fr))
if to:opa.append("commits are until %s"%(to))
opa.append("generated on %s"%datetime.datetime.now())
op+=' :: '.join(['<small>%s</small>'%ope for ope in opa])+'<br />'

op+="<h1>user totals</h1>"
op+=dtpat
uitems = by_user.items()
uitems.sort(srt2,reverse=True)
for user,commits in uitems:
    op+=mkrow(user,commits,commits=False)
op+=dtendpat
op+="<h1>project totals by date</h1>"
for proj,dates in project_date.items():
    op+="<h2>%s</h2>"%proj
    op+=dtpat
    commits = dates.items()
    commits.sort(srt3)
    for date,commit in commits:
        op+=mkrow(date,commit,commits=True)
    op+=dtendpat
op+="<h1>project totals by commiter</h1>"
for proj,commiters in  project_user.items():
    op+="<h2>%s</h2>"%proj
    op+=dtpat.replace('date','commiter')
    commits = commiters.items()
    commits.sort(srt2,reverse=True)
    for user,commit in commits:
        op+=mkrow(user,commit,commits=True)

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

