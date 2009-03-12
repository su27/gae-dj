#!/usr/bin/env python
#coding=utf-8

def readme():
    return '''
<pre>
GAE-DJ implemented a RESTful api for GAE database writing/reading and 
also for other GAE funny things like url fetching.

It's designed particularly for cross-domain javascript access.
check /static/*.html as demos.

author:damn.su@gmail.com


========database api=======

create(must login) or modify(must be creator) model:
    get /model/[MODEL_NAME]?[PARAS]

    PARAS can be:
    keys=key1,key2,key3,...     (required)
    canread=[all(default)|author|owner]
    canwrite=[all(default)|author|owner]
    canedit=[all|author(default)|owner]

insert record:
    get/post /post/[MODEL_NAME]?data={JSON}

modify record:
    get/post /modify/[MODEL_NAME]?data={JSON}

view record(s):
    get /view/[MODEL_NAME]/[KEY]/[VALUE]?op=[eq(default)|gt|lt|in]

    example:
    get /view/mm/marks/S'
    get /view/mm/marks/B_C_D?op=in'

delete record:
    get /delete/[MODEL_NAME]/[ID]


========fetch url===========

get/post /fetch?data={JSON}

    data is:
        url:    (required)
        method: GET|POST|PUT|DELETE|HEAD
        fields: {"key":"value"} (for POST/PUT)
        headers:{'Content-Type': 'application/x-www-form-urlencoded'}
        decode: GBK|...

    response:
            {'content':result.content,
            'truncated':result.content_was_truncated,
            'status_code':result.status_code}


=======user profile==========

get /profile
    response:{"loginurl":"localhost:8080", "user":"test@example.com"}


********************how to use js client******************


&lt;script type="text/javascript" src="/static/gae-dj.js"&gt;&lt;/script&gt;

var dj = new Gaedj();
dj.send('model/mm?keys=name,height',function(r){
    alert('try to make a model:'+r.success)
});

dj.send('fetch?data={"url":"http://g.cn/","decode":"gbk"}',function(r){
        $('#con').html(r.content)
})
</pre>
just check /static/*.html as demos!

<a href='/static/test.html'>data opreation demo</a> | 
<a href='/static/fetch.html>fetch demo</a>

'''
