import sys,urllib,re,datetime,json
import odesk
conf = json.loads(open('odesk_auth.json','r').read())
client = odesk.Client(conf['pub_key'],conf['priv_key'],conf['auth_token'])
def run_query(date_from,date_to,provider=None):
    if provider:
        fields = ['memo','worked_on','sum(hours)']
    else:
        fields = ['memo','worked_on','provider_id','provider_name','sum(hours)']

    odq = odesk.Query(select=fields, 
                      where=(odesk.Q('worked_on') <= date_to) &\
                          (odesk.Q('worked_on') >= date_from))
    if provider:
        res = client.\
            timereport.\
            get_provider_report(provider,odq,hours=False)
        raise Exception(res)
    else:
        res= client.\
            timereport.\
            get_team_report(conf['company_id'],conf['team_id'],odq , hours=True)
    return parse_result(res,date_from,date_to)


def parse_result(data,date_from,date_to,decode_users=True):
    #print 'parsing result %s'%data
    if (type(date_from)==datetime.date): date_from = date_from.strftime('%Y-%m-%d')
    if (type(date_to)==datetime.date): date_to = date_to.strftime('%Y-%m-%d')
    date_from_d = datetime.datetime.strptime(date_from,'%Y-%m-%d')
    date_to_d = datetime.datetime.strptime(date_to,'%Y-%m-%d')
    storyre = re.compile('([0-9]{3})')
    by_provider={}
    by_story={}
    by_provider_story={}
    by_story_provider={}
    by_provider_date={}
    total=0

    if 'table' not in data:
        raise Exception(data)
    cols = data['table']['cols']
    
    rawcols = [col['label'] for col in cols]

    for row in data['table']['rows']:
        dt={} ; cnt=0
        for rc in rawcols:
            dt[rc]=row['c'][cnt]['v']
            cnt+=1
        pid = dt['provider_id']
        if decode_users:
            if pid not in conf['usermap']:
                raise Exception('%s not found'%pid)
            pid = conf['usermap'][pid]

        hrs = float(dt['hours'])
        rowdate = datetime.datetime.strptime(dt['worked_on'],'%Y%m%d')
        rowdate_s = rowdate.strftime('%Y-%m-%d')
        if (rowdate<date_from_d or rowdate>date_to_d):
            raise Exception('got row from %s (outside of %s - %s)'%(rowdate,date_from_d,date_to_d))
            continue
        storyres = storyre.search(dt['memo'])
        if storyres:
            sid = storyres.group(1)
        else:
            sid = 'None'
        if pid not in by_provider: 
            by_provider[pid]=0
            by_provider_date[pid]={}
            by_provider_story[pid]={}

        if sid not in by_provider_story[pid]:
            by_provider_story[pid][sid]=0
        if sid not in by_story_provider: by_story_provider[sid]={}
        if pid not in by_story_provider[sid]: by_story_provider[sid][pid]=0
        if rowdate_s not in by_provider_date[pid]:
            by_provider_date[pid][rowdate_s]=0
        if sid not in by_story: 
            by_story[sid]=0
        by_provider[pid]+=hrs
        by_story[sid]+=hrs
        by_provider_date[pid][rowdate_s]+=hrs
        by_provider_story[pid][sid]+=hrs
        by_story_provider[sid][pid]+=hrs
        total+=hrs
    return {'by_provider':by_provider,'by_story':by_story,'total':total,'by_provider_date':by_provider_date,'by_provider_story':by_provider_story,'by_story_provider':by_story_provider}

def isort(i1,i2):
    return cmp(i1[1],i2[1])

def print_report(rt):
    if 'None' in rt['by_story_provider']:
        print '------------no story---------------'
        sbh = rt['by_story_provider']['None'].items()
        sbh.sort(isort)
        for k,v in sbh:
            print '%s\t%s'%(k,v)
    #raise Exception(rt['by_story_provider']['None'])
    print '------------by provider------------'
    bpi = rt['by_provider'].items()
    bpi.sort(isort)
    for k,v in bpi:
        print '%s\t%s'%(k,v)
    print '------------by story---------------'
    bsi = rt['by_story'].items()
    bsi.sort(isort)
    for k,v in bsi:
        print '%s\t%s'%(k,v)
    print '------\n%s hours in total'%rt['total']
def save_report(rt,fr,to):
    op='<!doctype html><html><head><title>hours report for %s - %s</title></thead><body>'%(fr,to)
    op+='<h1>odesk hours report for %s - %s</h1>'%(fr,to)
    op+='<p><b>%4.1f</b> hours logged in total</p>'%rt['total']
    op+='<h2>by provider</h2><table><thead><tr><th>provider</th><th>hours</th></tr></thead><tbody>'
    for k,v in rt['by_provider'].items():
        op+='<tr><td>%s</td><td style="text-align:right">%4.1f</td></tr>'%(k,v)
    op+='</tbody></table>';

    op+='<h2>by story</h2><table><thead><tr><th>provider</th><th>hours</th></tr></thead><tbody>'
    for k,v in rt['by_story'].items():
        op+='<tr><td>%s</td><td style="text-align:right">%4.1f</td></tr>'%(k,v)
    op+='</tbody></table>';

    op+='<h2>by provider and story</h2><table><tr><th>provider</th><th>story</th><th>hours</th></tr></thead><tbody>'
    for u,v in rt['by_provider_story'].items():
        for s,d in v.items():
            op+='<tr><td>%s</td><td>%s</td><td style="text-align:right">%4.1f</td></tr>'%(u,s,d)

    op+='</tbody></table>'

    op+='</body></html>'

    fn = 'hours-%s:%s.html'%(fr,to)
    fp = open(fn,'w')
    fp.write(op);
    fp.close()
    print 'written to %s'%fn

if __name__=='__main__':
    fr,to = sys.argv[1].split(':')
    if to=='today': to = datetime.datetime.now().strftime('%Y-%m-%d')
    if fr=='today': fr = datetime.datetime.now().strftime('%Y-%m-%d')

    #nw = datetime.datetime.now().date() ; date_from = nw - datetime.timedelta(days=30) ; date_to = nw
    if len(sys.argv)>2 and sys.argv[2]=='test':
        from tdata import data
        rt = parse_result(data,date_from=fr,date_to=to)
    elif len(sys.argv)>2:
        rt = run_query(date_from=fr,date_to=to,provider=sys.argv[2])
    else:
        rt = run_query(date_from=fr,date_to = to)
    print_report(rt)
    save_report(rt,fr,to)
    
