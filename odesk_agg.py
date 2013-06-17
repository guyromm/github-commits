import sys
import re
import odesk
import json
import datetime
from orm import *

conf = json.loads(open('odesk_auth.json','r').read())
client = odesk.Client(conf['pub_key'],
                      conf['priv_key'],
                      conf['auth_token'])

fields = ['memo',
          'worked_on',
          'provider_id',
          'provider_name',
          'sum(hours)',
          ]
dt = s.query(sa.func.max(OdeskWork.worked_on)).one()[0]
nw = datetime.datetime.now()
if not dt: 
    dt = datetime.datetime(year=nw.year,month=nw.month,day=1)
date_from=dt
date_to=nw.date()
odq = odesk.Query(select=fields, 
                  where=(odesk.Q('worked_on') <= date_to) &\
                      (odesk.Q('worked_on') >= date_from))

dtpre = re.compile('^(\d{4})(\d{2})(\d{2})$')
taskre = re.compile('([\d\/]+)')

res= client.\
    timereport.\
    get_team_report(conf['company_id'],conf['team_id'],odq , hours=True)
if len(res['table']['rows']):
    for o in s.query(OdeskWork).filter(OdeskWork.worked_on==dt).all():
        s.delete(o)
    s.commit()
for row in res['table']['rows']: 
    #{u'c': [{u'v': u'#666'}, {u'v': u'20130615'}, {u'v': u'islava'}, {u'v': u'Vyacheslav Linnik'}, {u'v': u'6.833333'}]}
    dtpres = dtpre.search(row['c'][1]['v']).groups()
    won = datetime.datetime(year=int(dtpres[0]),month=int(dtpres[1]),day=int(dtpres[2]))
    memo = row['c'][0]['v']
    taskres = taskre.search(memo)
    if taskres:
        task = taskres.group(1)
    else:
        print 'could not parse task from %s'%row['c'][0]['v']
        task=None

    ow = OdeskWork()
    ow.provider = row['c'][2]['v']
    ow.worked_on = won
    ow.memo = memo
    ow.task = task
    ow.hours = float(row['c'][4]['v'])
    print row
    s.add(ow) ; s.commit()

    #print row
