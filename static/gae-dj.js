function Gaedj(server){
    this.server = server || "http://hellodj.appspot.com/";
}
Gaedj.cb = [];

Gaedj.addcb = function(cb){
    Gaedj.cb.push(cb);
    return Gaedj.cb.length-1
}

Gaedj.prototype.nload = function(file,callback){
    var userAgent = navigator.userAgent.toLowerCase();
    var msie = /msie/.test(userAgent) && !/opera/.test(userAgent);
    var e = document.createElement('script');
    e.setAttribute('language','javascript');
    e.setAttribute('type','text/javascript');
    e.setAttribute('src',file);
    document.getElementsByTagName('head')[0].appendChild(e);
    if(callback){
        if(msie){
            e.onreadystatechange = function(){
                if(this.readyState==='loaded'||
                    this.readyState==='complete'){
                    callback()
                }
            }
        } else { e.onload = callback }
    }
}

Gaedj.prototype.send = function(url,cb){
    var url = this.server+url+(url.indexOf('?') == -1? '?':'&')
        +'callback=Gaedj.cb['+Gaedj.addcb(cb)+']'
    this.nload(url);
}
