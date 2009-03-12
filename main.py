#!/usr/bin/env python
#coding=utf-8

import cgi
import logging
import os
import re
from urllib import unquote, quote, urlencode
from datetime import datetime
import wsgiref.handlers
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import users,memcache,urlfetch
from google.appengine.api.urlfetch import InvalidURLError,\
        DownloadError
import simplejson
from doc import readme

class Modinfo(db.Model):
    acc = db.UserProperty()
    djname = db.StringProperty()
    keys = db.StringListProperty()
    # 'owner', 'author', anyelse
    canwrite = db.StringProperty()
    canedit= db.StringProperty()
    canmodify = db.StringProperty()
    canread = db.StringProperty()

class Record(db.Expando):
    djname = db.StringProperty()
    djauthor = db.UserProperty()

op_map = {'gt':'>', 'lt':'<', 'in':'IN', 'eq':'='}
met_map = {'GET':urlfetch.GET,
            'POST':urlfetch.POST,
            'HEAD':urlfetch.HEAD,
            'PUT':urlfetch.PUT,
            'DELETE':urlfetch.DELETE,
            }
err_map = {1:'not enough arguments',
           2:'cannot modify the model,maybe need login',
           3:'need some parameters',
           4:'login required',
           5:'you cannot write on the model',
           6:'you cannot read the model',
           7:'cannot get record with such id',
           8:'you cannot delete the record',
           9:'contains a field name that is not allowed',
           10:'error when querying data',
           11:'url is required',
           12:'invalid url',
           13:'error when downloading',
           14:'error when fetching the url',
          }

def greeting(user, redir='/'):
    return user and (
            "<strong>%s</strong> (<a href='%s'> logout</a>)" 
            % (user.nickname().split('@')[0],
            users.create_logout_url(redir))) or \
            ("<a href='%s'>login with Google account</a>" %
            users.create_login_url(redir))

def needparas(n):
    def pre(f):
        def wrap(req):
            paras = req.path[1:].split('/')
            req.paras = [p for p in paras if p!='']
            return len(req.paras)<n and msg(1) or f(req)
        return wrap
    return pre

def msg(errno,**res):
    if errno == 0:
        res['success'] = 1
    else:
        res['success'] = 0
        res['error'] = err_map[errno]
    return res

def authmod(modname,d=None):
    user = users.GetCurrentUser()
    mod = memcache.get('modinfo:'+modname)
    if mod is None:
        mod = Modinfo.all().filter('djname =',modname)
        if not memcache.add('modinfo:'+modname, mod, 3600*24*7):
            logging.error('memcache failed')
    if mod.count() == 0:
        return {'canwrite':False,'canread':False,'canedit':False,
                'canmodify':(user!=None),'modinfo':None}
    m = mod[0]
    can_do_as = {'owner':(user and m.acc==user),
                'author':user and (m.acc==user or \
                        (d and d.djauthor==user)),
                }
    return {'canwrite':can_do_as.get(m.canwrite,True), 
            'canread':can_do_as.get(m.canread,True),
            'canedit':can_do_as.get(m.canedit,False),
            'canmodify':can_do_as.get('owner'),
            'modinfo':m,
            }

@needparas(2)
def handle_post(request):
    user = users.GetCurrentUser()
    data = request.get('data','{}')
    data = simplejson.loads(data)
    modname = request.paras[1]
    if not authmod(modname)['canwrite']:
        return msg(5)
    da = {}
    for k in data:
        try:
            v = int(data[k])
        except:
            v = data[k]
        da[str(k)] = v
    r = Record(djname=modname, djauthor=user, **da)
    r.put()
    memcache.delete('djname:'+modname)
    return msg(0,id=r.key().id())

@needparas(2)
def handle_modify(request):
    paras = request.paras
    modname, id = paras[1], paras[2]
    try:
        r = Record.get_by_id(int(id))
    except:
        return msg(7)
    if not authmod(modname,d=r)['canedit']:
        return msg(8)
    data = request.get('data','{}')
    data = simplejson.loads(data)
    da = {}
    for k in data:
        try:
            v = int(data[k])
        except:
            v = data[k]
        exec('r.'+str(k) +'= v')
    r.put()
    memcache.delete('djname:'+modname)
    return msg(0,id=r.key().id())

@needparas(2)
def handle_view(request):
    user = users.GetCurrentUser()
    paras = request.paras
    op = request.get('op',None)
    modname = paras[1]
    info = authmod(modname)
    if not info['canread']:
        return msg(6)
    op = op_map.get(op, '=')

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
            if op in ['<','>']:
                try:
                    v = int(paras[3])
                except ValueError:
                    pass
            elif op == 'IN':
                v = paras[3].split('_')
                records = Record.gql(
                        'WHERE djname = :name AND %s IN :v' 
                        % paras[2], name=modname,v=v)
            else:
                v = paras[3]
                records.filter('%s %s' % (paras[2],op), v)

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

@needparas(3)
def handle_delete(request):
    paras = request.paras
    modname = paras[1]
    id = paras[2]
    try:
        r = Record.get_by_id(int(id))
    except:
        return msg(7)
    if r is None:
        return msg(7)
    if not authmod(modname,d=r)['canedit']:
        return msg(8)
    r.delete()
    memcache.delete('djname:'+modname)
    return msg(0)

@needparas(2)
def handle_model(request):
    user = users.GetCurrentUser()
    modname = request.paras[1]
    info = authmod(modname)
    #logging.info(info)
    if not info['canmodify']:
        return msg(2)
    m = info['modinfo'] and info['modinfo'] or Modinfo(acc=user, \
            djname=modname)
    m.keys = request.get('keys','').split(',')
    #TODO: validate keys
    if ('id' in m.keys) or ('mydj' in m.keys):
        return msg(9)
    m.canwrite = request.get('canwrite','all')
    m.canread = request.get('canread','all')
    m.canedit = request.get('canedit','author')
    m.put()
    memcache.delete('modinfo:'+modname)
    return msg(0)

def handle_fetch(request):
    data = request.get('data','{}')
    data = simplejson.loads(data)
    url = data.get('url',None)
    if url is None:
        return msg(11)
    met = data.get('method',None)
    fetchreq = {'url':url,'method':met_map.get(met, urlfetch.GET)}
    fields = data.get('fields',None)
    headers = data.get('headers',None)
    codec = data.get('decode',None)
    if fields is not None:
        fetchreq['payload'] = urlencode(fields)
    if headers is not None:
        fetchreq['headers'] = headers
    try:
        result = urlfetch.fetch(**fetchreq)
    except InvalidURLError:
        return msg(12,url=url)
    except DownloadError:
        return msg(13,url=url)
    except:
        return msg(14,url=url)
    if codec is None:
        content = result.content
    else:
        try:
            content = result.content.decode(codec)
        except:
            content = result.content

    return {'content':content,'status_code':result.status_code,
            'truncated':result.content_was_truncated}

class AllHandler(webapp.RequestHandler):
    def jsout(self,json):
        self.response.headers["Content-Type"] = "text/javascript"
        callback = self.request.get('callback','//')
        #self.response.out.write('tr("%s");' % self.request.url)
        s = '%s(%s);' % (callback, simplejson.dumps(json))
        self.response.out.write(s)

class PostHandler(AllHandler):
    def get(self):
        self.jsout(handle_post(self.request))
    def post(self):
        self.jsout(handle_post(self.request))

class ViewHandler(AllHandler):
    def get(self):
        self.jsout(handle_view(self.request))

class DeleteHandler(AllHandler):
    def get(self):
        self.jsout(handle_delete(self.request))

class ModifyHandler(AllHandler):
    def get(self):
        self.jsout(handle_modify(self.request))
    def post(self):
        self.jsout(handle_modify(self.request))

class ModelHandler(AllHandler):
    def get(self):
        self.jsout(handle_model(self.request))

class FetchHandler(AllHandler):
    def get(self):
        self.jsout(handle_fetch(self.request))

    def post(self):
        self.jsout(handle_fetch(self.request))

class ProfileHandler(AllHandler):
    def get(self):
        user = users.GetCurrentUser()
        name = user and user.nickname() or ''
        loginurl = 'http://'+os.environ['HTTP_HOST']
        self.jsout({'user':name,'loginurl':loginurl})
        #for name in os.environ.keys():
        #    self.response.out.write("%s = %s<br />\n" % (name, os.environ[name]))

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(greeting(users.GetCurrentUser()))
        self.response.out.write(readme())

def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                    ('/post/.*', PostHandler),
                                    ('/delete/.*', DeleteHandler),
                                    ('/view/.*', ViewHandler),
                                    ('/model/.*',ModelHandler),
                                    ('/modify/.*',ModifyHandler),
                                    ('/fetch.*',FetchHandler),
                                    ('/profile.*',ProfileHandler),
                                    ('/.*',MainHandler),
                                        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()
