#!/usr/bin/env python

import cgi
import logging
from urllib import unquote,quote
from datetime import datetime
import wsgiref.handlers
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import users
from google.appengine.api import memcache
import simplejson

user = users.GetCurrentUser()

class Modinfo(db.Model):
    acc = db.UserProperty()
    djname = db.StringProperty()
    keys = db.StringListProperty()
    # 'owner', 'author', whatever
    canwrite = db.StringProperty()
    candelete = db.StringProperty()
    canread = db.StringProperty()

class Record(db.Expando):
    djname = db.StringProperty()
    djauthor = db.UserProperty()

op_map = {'gt':'>', 'lt':'<', 'in':'IN', 'eq':'='}

def greeting(user, redir='/'):
    return user and ("<strong>%s</strong> (<a href='%s'>\
            logout</a>)" % (user.nickname().split('@')[0],
            users.create_logout_url(redir))) or \
            ("<a href='%s'>login with Google account</a>" %
            users.create_login_url(redir))

def msg(errno):
    if errno == 0:
        return {'success':1}
    err_map = {1:'not enough arguments',
                2:'cannot modify the model,maybe need login',
                3:'need some parameters',
                4:'login required',
                5:'you cannot write on the model',
                6:'you cannot read the model',
                7:'cannot get record with such id',
                8:'you cannot delete the record',
                9:'contains a field name that is not allowed',
                }
    return {'success':0,'error':err_map[errno]}

def authmod(modname,d=None):
    mod = Modinfo.all().filter('djname =',modname)
    if mod.count() == 0:
        return {'canwrite':False,'canread':False,
                'canmodify':(user!=None),'modinfo':None}
    m = mod[0]
    can_do_as = {'owner':(m.acc==user),
                'author':(m.acc==user or \
                        (d and d.djauthor==user)),
                }
    return {'canwrite':can_do_as.get(m.canwrite,True), 
            'canread':can_do_as.get(m.canread,True),
            'candelete':can_do_as.get(m.candelete,False),
            'canmodify':can_do_as.get('owner'),
            'modinfo':m,
            }

def handle_post(request):
    data = request.get('data','{}')
    data = simplejson.loads(data)
    paras = request.path[1:].split('/')
    if len(paras)<2:
        return msg(1)
    modname = paras[1]
    if not authmod(modname)['canwrite']:
        return msg(5)
    da = {}
    for k in data:
        da[str(k)] = str(data[k])
    rec = Record(djname=modname,**da)
    rec.put()
    memcache.delete('djname:'+modname)
    return msg(0)

def handle_view(request):
    op = request.get('op',None)
    try:
        op = op_map[op]
    except:
        op = '='
    paras = request.path[1:].split('/')
    if len(paras)<2:
        return msg(1)
    modname = paras[1]
    info = authmod(modname)
    if not info['canread']:
        return msg(6)
    
    records = memcache.get('djname:'+modname)
    if records is None:
        records = Record.all().filter('djname =', modname)
        if not memcache.add('djname:'+modname, records, 3600*24*7):
            logging.error('memcache failed')
        if records.count() == 0:
            return []

    if len(paras)>3:
        if paras[2] == 'id':
            try:
                res = Record.get_by_id(int(paras[3]))
                records = [res]
            except:
                return msg(7)
        elif paras[2] == 'mydj':
            records.filter('author =',user)
        else:
            records.filter('%s %s' % (paras[2],op), paras[3])

    res = []
    for r in records:
        ob = {}
        for key in info['modinfo'].keys:
            try:
                ob[key] = eval('r.'+key)
            except AttributeError:
                ob[key] = ''
        ob['id'] = r.key().id()
        res.append(ob)
    return res

def handle_delete(request):
    paras = request.path[1:].split('/')
    if len(paras)<3:
        return msg(1)
    modname = paras[1]
    id = paras[2]
    try:
        r = Record.get_by_id(int(id))
    except:
        return msg(7)
    if not authmod(modname,d=r)['candelete']:
        return msg(8)
    r.delete()
    memcache.delete('djname:'+modname)
    return msg(0)

def handle_model(request):
    paras = request.path[1:].split('/')
    if len(paras)<2:
        return msg(1)
    modname = paras[1]
    info = authmod(modname)
    if not info['canmodify']:
        return msg(2)
    m = info['modinfo'] and info['modinfo'] or Modinfo(acc=user, \
            djname=modname)
    m.keys = request.get('keys','').split(',')
    if ('id' in m.keys) or ('mydj' in m.keys):
        return msg(9)
    m.canwrite = request.get('canwrite','all')
    m.canread = request.get('canread','all')
    m.candelete = request.get('candelete','author')
    m.put()
    return msg(0)

class AllHandler(webapp.RequestHandler):
    def jsout(self,json):
        self.response.headers["Content-Type"] = "text/javascript"
        callback = self.request.get('callback','//')
        s = '%s(%s);' % (callback, simplejson.dumps(json))
        self.response.out.write(s)

class PostHandler(AllHandler):
    def get(self):
        self.jsout(handle_post(self.request))

class ViewHandler(AllHandler):
    def get(self):
        self.jsout(handle_view(self.request))

class DeleteHandler(AllHandler):
    def get(self):
        self.jsout(handle_delete(self.request))

class ModelHandler(AllHandler):
    def get(self):
        self.jsout(handle_model(self.request))

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(greeting(users))

def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                    ('/post/.*', PostHandler),
                                    ('/delete/.*', DeleteHandler),
                                    ('/view/.*', ViewHandler),
                                    ('/model/.*',ModelHandler),
                                        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()
