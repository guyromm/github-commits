from commands import getstatusoutput as gso
from orm import *
import re
import os
import sys
import datetime
from dulwich.repo import Repo as DRepo

st,op = gso('which git-new-workdir') ; assert st==0
cachedir = '~/Projects/scratch-repos-cache'
taskre = re.compile('\#([\d\/]+)')
mydir = './repos'
rc={} #cache
repos = s.query(Repo).all()

for r in repos:
    rdir = os.path.join(mydir,r.name)
    if not os.path.exists(rdir):
        st,op = gso('git-new-workdir %s %s'%(os.path.join(cachedir,r.name),
                                             rdir))
        assert st==0
    if 'fetch' in sys.argv:
        st,op = gso('cd %s && git fetch -a'%rdir) ; assert st==0

    st,op = gso('cd %s && git rev-list --since=2013-06-01 --remotes'%rdir); 
    assert st==0
    for revid in op.split('\n'):
        cm = s.query(Commit).\
            filter(Commit.repo==r.name).\
            filter(Commit.rev==revid).first()
        if cm: continue
        if rdir not in rc:
            rc[rdir] = DRepo(rdir)
        dr = rc[rdir]

        o = dr.get_object(revid)

        taskres = taskre.search(o.message.strip())
        if taskres: task = taskres.group(1)
        else: task = None



        cm = Commit()
        cm.repo = r.name
        cm.rev = revid
        cm.author = o.author
        cm.message = o.message.strip()
        cm.task = task
        cm.commited_on = datetime.datetime.fromtimestamp(o.commit_time)
        cm.size = o.raw_length()
        s.add(cm) ; s.commit()
