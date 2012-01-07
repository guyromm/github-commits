#!/usr/bin/python

import json,glob,os,datetime,re,sys,codecs
from commands import getstatusoutput as gso
from odesk_fetch import run_query,parse_result


def run(fr=None,to=None,rcpt=[],makereport=False,odesk=True,all_odesk_users=False,branches=['master'],repos=None,exclude_users=[],only_users=[]):

    #do the odesk dance
    usermap = {}

    storyre= re.compile(re.escape('#')+'([0-9]+)')

    conf = json.loads(open('config.json','r').read().replace('\n',''))
    GITHUB_USER = conf['user'] #open('githubuser.txt','r').read().strip()
    GITHUB_PASSWORD = conf['user']+':'+conf['password'] #open('githubpw.txt','r').read().strip()
    GITHUB_PROJECTS = conf['projects'] #open('githubprojects.txt','r').read().strip().split('\n')
    usermapjson = conf['usermap']
    for k,v in usermapjson.items():
        usermap[re.compile(re.escape(k))]=[v,k]

    by_story={}
    by_user_story={}
    by_user={}
    by_branch={}
    by_project={}

    by_date={}

    user_project={}
    project_user={}
    user_date={}
    user_project_date={}
    project_date={}

    projbranches={}
    projects_commits={}

    lprojs = GITHUB_PROJECTS+repos
    for proj in lprojs:
        if repos and proj not in repos:
            continue
        if 'all' in branches:
            cmd = "curl -s -u '%s' 'http://github.com/api/v2/json/repos/show/%s/%s/branches'"%(GITHUB_PASSWORD,GITHUB_USER,proj)
            st,op = gso(cmd) ; assert st==0
            bop = json.loads(op)
            mybranches = bop['branches'].keys()
            projbranches[proj]=mybranches
        else:
            mybranches = branches
            projbranches[proj]=mybranches

        bcnt=0
        for branch in mybranches:
            bcnt+=1
            print 'going for branch %s, %s/%s to get'%(branch,bcnt,len(mybranches))
            ofn = os.path.join('data','%s:%s.json'%(proj,branch))
            fetchnew=True ; lastcommit=None

            #decide whether to really fetch the commits list based on whether the file exists
            if os.path.exists(ofn):
                st = os.stat(ofn)
                fmt = datetime.datetime.fromtimestamp(st.st_mtime)
                oneh = (datetime.datetime.now()-datetime.timedelta(days=1))
                if fmt>=oneh:fetchnew=False
                else:
                    lcop = json.loads(open(ofn,'r').read())
                    if len(lcop['commits']):
                        myc = lcop['commits'][0]
                        lastcommit = datetime.datetime.strptime(myc['authored_date'][0:-5],'%Y-%m-%dT%H:%M:%S-')
                    #raise Exception('last commit on %s'%lastcommit)
                    #os.unlink(ofn)
                print 'fmt = %s; oneh = %s; fetchnew = %s; lastcommit = %s'%(fmt,oneh,fetchnew,lastcommit)
                
            if fetchnew:
                print 'fetching project %s / %s'%(proj,branch)
                pagenum=1
                wr={'commits':[]}
                while True:
                    print 'taking page %s'%pagenum
                    tries=0
                    cmd = "curl --max-time 5 -s -u '%s' 'http://github.com/api/v2/json/commits/list/%s/%s/%s?page=%s'"%(GITHUB_PASSWORD,GITHUB_USER,proj,branch,pagenum)

                    print cmd
                    while True:
                        if tries>7: raise Exception('too many tries at %s'%cmd)
                        st,op=gso(cmd) ; 
                        if st!=0:
                            tries+=1
                            print "curl returned %s. try %s"%(st,tries)
                        else:
                            break

                    print '%s bytes received'%(len(op))
                    dt = json.loads(op)
                    if pagenum==1 and lastcommit:
                        myc = dt['commits'][0]
                        lastcommit2 = datetime.datetime.strptime(myc['authored_date'][0:-5],'%Y-%m-%dT%H:%M:%S-')
                        print('saved last commit = %s ; fetched last commit = %s;'%(lastcommit,lastcommit2))
                        if lastcommit==lastcommit2:
                            print 'last commits match. touching existing file and moving on.'
                            st,op = gso('touch %s'%ofn) ; assert st==0
                            break
                        elif lastcommit<lastcommit2:
                            print 'existing last commit is older than one recieved. deleting existing file %s'%ofn
                            os.unlink(ofn)
                        else:
                            raise Exception('how could it be that a saved commit is newer than retrieved on %s?'%ofn)

                    pagenum+=1
                    if 'commits' in dt: print '%s entries'%len(dt['commits'])
                    if 'commits' not in dt or not len(dt['commits']): 
                        if pagenum<1:
                            raise Exception('no commits in %s,%s'%(proj,pagenum))
                        break
                    wr['commits']+=dt['commits']

                fp = open(ofn,'w') ; fp.write(json.dumps(wr)); fp.close()
                print 'written to %s'%ofn

        else:
            print '%s is recent enough'%proj

    def initarr():
        return {'times':0,'diff':0,'removed':0,'added':0,'ids':[],'hours':0}


    print 'generation phase.'
    comre = re.compile('([a-f0-9]{16})')
    projre = re.compile('^data/(.*)\:(.*)\.json$')
    repos_branches_processed={}

    for fn in glob.glob('data/*.json'):
        if comre.search(fn): continue
        #raise Exception(fn)
        projres = projre.search(fn)
        if not projres: raise Exception('dunno %s'%fn)
        fproj = projres.group(1)
        fbranch = projres.group(2)

        if fproj not in projbranches or fbranch not in projbranches[fproj]:
            #print('not supposed to do branch %s on %s (%s)'%(fbranch,fproj,projbranches[fproj]))
            continue
        obj = json.loads(open(fn,'r').read())


        print 'going over proj %s'%(fn)

        assert 'commits' in obj,'cannot find commits in %s'%fn
        print 'project has %s commits' %(len(obj['commits']))
        for c in obj['commits']:
            projfn = os.path.basename(fn).replace('.json','')

            comfn = os.path.join('data','%s.%s.json'%(fproj,c['id']))

            user = c['committer']['email']
            for um,uv in usermap.items():
                #print 'trying to match %s -> %s'%(uv[1],user)
                if um.search(user):
                    user = uv[0]
                    break

            assert user,c
            proj = os.path.basename(fn).replace('.json','')
            date = datetime.datetime.strptime(c['authored_date'][0:-5],'%Y-%m-%dT%H:%M:%S-') #dateutil.parser.parse(c['authored_date'])
            #print 'fr = %s ; to = %s; date = %s'%(fr,to,date.date())
            if fr and date.date()<fr: continue
            if to and date.date()>to: continue
            #print '%s -> %s on %s'%(user,proj,date)

            if fproj not in repos_branches_processed: repos_branches_processed[fproj]=[]
            if fbranch not in repos_branches_processed[fproj]: repos_branches_processed[fproj].append(fbranch)

            comid = '/%s/%s/commit/%s'%(GITHUB_USER,fproj,c['id'])
            
            #skip this commit if we already covered it.
            if fproj not in projects_commits: projects_commits[fproj]=[]
            if c['id'] not in projects_commits[fproj]: 
                projects_commits[fproj].append(c['id'])
            else:
                print('already aggregated %s/%s'%(fproj,c['id']))
                continue
            #register the stories mentioned in the commit
            stories=[]
            for cr in storyre.finditer(c['message']):
                story_id = cr.group(1)
                stories.append(story_id)
            if not len(stories):
                stories.append('None')

            commsg = c['message']
            if not os.path.exists(comfn):
                print 'fetching commit %s'%c['id']
                comurl = 'http://github.com/api/v2/json/commits/show/%s/%s/%s'%(GITHUB_USER,fproj,c['id'])
                curlcmd = 'curl -u %s %s > %s'%(GITHUB_PASSWORD,comurl,comfn)
                st,op = gso(curlcmd) ; assert st==0
                assert os.path.exists(comfn)
            try:
                comdt = json.loads(open(comfn).read())
            except:
                raise Exception('could not load from %s'%comfn)

            if 'commit' not in comdt:
                print 'could not figure out %s'%comfn
                raise Exception(comdt)

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

            if fproj not in project_date: project_date[fproj]={}
            if fproj not in project_user: project_user[fproj]={}
            if user not in project_user[fproj]: project_user[fproj][user]=initarr()
            if date.date() not in project_date[fproj]: project_date[fproj][date.date()] = initarr()

            if user not in by_user: 
                user_project_date[user]={}
                user_date[user]={}
                user_project[user]={}
                by_user[user]=initarr()

            if fbranch not in by_branch:
                by_branch[fbranch]=initarr()

            def idsort(i1,i2):
                return cmp(i1[3],i2[3])
            def incr(o):
                #global dfsum,added,removed,comid,commsg
                o['times']+=1
                o['diff']+=dfsum
                o['removed']+=removed
                o['added']+=added
                o['ids'].append([comid,commsg,user,date])
                o['ids'].sort(idsort)
            for storyid in stories:
                if storyid not in by_story:
                    by_story[storyid]=initarr()
                tok = '#%s by %s'%(storyid,user)
                if tok not in by_user_story:
                    by_user_story[tok]=initarr()
                incr(by_story[storyid])
                incr(by_user_story[tok])

            incr(by_user[user])
            incr(by_branch[fbranch])
            incr(project_user[fproj][user])
            if fproj not in by_project: 
                by_project[fproj]=initarr()

            if fproj not in user_project[user]:
                user_project[user][fproj]=initarr()

            incr(user_project[user][fproj])
            incr(by_project[fproj])

            if date.date() not in by_date: 
                by_date[date.date()]=initarr()

            if date.date() not in user_date[user]:
                user_date[user][date.date()]=initarr()

            if fproj not in user_project_date[user]: user_project_date[user][fproj]={}
            if date.date() not in user_project_date[user][fproj]: user_project_date[user][fproj][date.date()]=initarr()

            incr(project_date[fproj][date.date()])
            incr(user_project_date[user][fproj][date.date()])
            incr(by_date[date.date()])
            incr(user_date[user][date.date()])

    if odesk:    #we get the odesk hours query
        print 'odesk hours phase.'
        res = run_query(fr,to)

        #and populate the relevant trees with our yummy new data
        for user,dates in res['by_provider_date'].items():
            if user not in user_date: 
                if not all_odesk_users: continue
                if user in exclude_users: continue
                if only_users and user not in only_users: continue
                user_date[user]={}
            if user not in by_user: by_user[user]=initarr()
            for dt,hrs in dates.items():
                mdt = datetime.datetime.strptime(dt,'%Y-%m-%d').date()
                if mdt not in user_date[user]: user_date[user][mdt]=initarr()
                user_date[user][mdt]['hours']+=hrs
                by_user[user]['hours']+=hrs
        #also by user/story
        for user,stories in res['by_provider_story'].items():
            for sid,hrs in stories.items():
                usl = '#%s by %s'%(sid,user)
                sid = '#'+sid
                if usl not in by_user_story: 
                    if not all_odesk_users: continue
                    if user in exclude_users: continue
                    if only_users and user not in only_users: continue
                    by_user_story[usl]=initarr()
                by_user_story[usl]['hours']+=hrs
        
    if not makereport:
        return {'by_user':by_user,'by_story':by_story}

    def srtit(a1,a2):
        return cmp(a1[0],a2[0])
    def srt2(i1,i2):
        try:
            rt= cmp(i1[1]['hours'],i2[1]['hours'])
        except:
            print (i1[1],i2[1])
            raise
        return rt
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
            curi = item[1]['hours']
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
    <h1>users/days hours chart</h1>
    <div id='info'></div>
    """%(json.dumps(jsexp))

    dtpat = "<table><thead><tr><th>date<th>commits<th>added<th>removed<th>difflines<th>hours<th>l/h</th><th>links</tr></thead><tbody>\n"
    dtendpat = "</tbody></table>"
    rowpat = "<tr><td><nobr>%s</nobr></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%3.1f</td><td>%3.1f</td><td>%s</td></tr>\n"
    def mkrow(date,dt,commits=True):
        if commits:
            cm = ', '.join(["<a href='https://github.com%s' title='%s by %s on %s'>%s</a>"%(com,commsg,user,stamp,com.split('/')[4][0:4]) for com,commsg,user,stamp in dt['ids']])

        else:
            cm=''
        if dt['hours']: 
            lbh=(dt['diff']/dt['hours'])
        else: 
            lbh=0
        rt= rowpat%(date,dt['times'],dt['added'],dt['removed'],dt['diff'],dt['hours'],lbh,cm)
        return rt
    opa=[]
    if fr:opa.append("commits are starting from %s"%(fr))
    if to:opa.append("commits are until %s"%(to))
    opa.append("generated on %s. repos/branches: %s"%(datetime.datetime.now(),repos_branches_processed))
    op+=' :: '.join(['<small>%s</small>'%ope for ope in opa])+'<br />'

    op+="<h1>user totals</h1>"
    op+=dtpat.replace('date','user')
    uitems = by_user.items()
    uitems.sort(srt2,reverse=True)
    for user,commits in uitems:
        op+=mkrow(user,commits,commits=False)
    op+=dtendpat

    op+="<h1>branch totals</h1>"
    op+=dtpat.replace('date','branch')
    uitems = by_branch.items()
    uitems.sort(srt2,reverse=True)
    for user,commits in uitems:
        op+=mkrow(user,commits,commits=True)
    op+=dtendpat
    
    
    op+="<h1>story/user totals</h1>"
    op+=dtpat.replace('date','story')
    sitems = by_user_story.items()

    sitems.sort(srt2,reverse=True)
    for storyid,commits in sitems:
        op+=mkrow(storyid,commits,commits=True)

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
    if not rcpt:
        fp = codecs.open(ofn,'w','utf-8') ; fp.write(op) ; fp.close()
        print 'written to %s'%ofn
    else:
        srvr = conf['smtp_server']
        port = conf['smtp_port']
        un = conf['smtp_user']
        pw = conf['smtp_pw']
        sender = conf['smtp_sender']

        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        fromaddr = sender
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'project commits for %s - %s'%(fr,to)
        msg['From'] = sender
        #msg['Reply-To'] = sender
        part2 = MIMEText(op, 'html')
        msg.attach(part2)

        # Credentials (if needed)
        username = un
        password = pw

        # The actual mail send
        server = smtplib.SMTP('%s:%s'%(srvr,port))

        server.starttls()
        server.login(username,password)
        for rc in rcpt:
            print 'mailing to %s -> %s'%(fromaddr,rc)
            toaddrs  = rc
            msg['To']=rc
            server.sendmail(fromaddr, toaddrs, msg.as_string())
        server.quit()

if __name__=='__main__':
    args={}
    for arg in sys.argv[1:]:
        argp = re.compile('^--(.*)\=(.*)$').search(arg)
        if not argp: raise Exception('unparsed %s'%arg)
        args[argp.group(1)]=argp.group(2)

    # if len(sys.argv)>1:
    #     fr,to = [datetime.datetime.strptime(it,'%Y-%m-%d').date() for it in sys.argv[1].split(':')]
    #     print 'report is for range %s - %s'%(fr,to)
    # else:
    #     fr,to = None,None
    for fn in ['fr','to','rcpt','repos']:
        if fn not in args: args[fn]=None
    if args['fr']: args['fr'] = datetime.datetime.strptime(args['fr'],'%Y-%m-%d').date()
    if args['to']: args['to'] = datetime.datetime.strptime(args['to'],'%Y-%m-%d').date()
    
    if args['rcpt'] and args['rcpt'][0]=='@': args['rcpt'] = open(args['rcpt'][1:],'r').read().split(',')
    elif args['rcpt']: args['rcpt'] = args['rcpt'].split(',')
    for fn in ['branches','repos','exclude_users','only_users']:
        if fn in args:
            if args[fn]: args[fn] = args[fn].split(',')

    args['all_odesk_users']=bool(args['all_odesk_users'])
    args['makereport']=True
    run(**args) #makereport=True,fr=args['fr'],to=args['to'],rcpt=args['rcpt'],branches=args['branches'],repos=args['repos'],all_odesk_users=args['all_odesk_users'])
