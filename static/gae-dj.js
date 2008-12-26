function Gaedj(server){
    this.server = server || "http://hellodj.appspot.com/";
}
Gaedj.cb = [];

Gaedj.addcb = function(cb){
    Gaedj.cb.push(cb);
    return Gaedj.cb.length-1
}

Gaedj.prototype.nload = function(file){
    var userAgent = navigator.userAgent.toLowerCase();
    var msie = /msie/.test(userAgent) && !/opera/.test(userAgent);
    var e = document.createElement('script');
    e.setAttribute('language','javascript');
    e.setAttribute('type','text/javascript');
    e.setAttribute('src',file);
    var head = document.getElementsByTagName('head')[0];
    head.appendChild(e);
    var cleanup = function(){
        setTimeout(function(){
            try{head.removeChild(e)}catch(err){}
        },100)
    };
    if(msie){
        e.onreadystatechange = function(){
            if(this.readyState==='loaded'||
                this.readyState==='complete'){
                cleanup()
            }
        }
    } else { e.onload = cleanup }
}

Gaedj.prototype.send = function(url,cb){
    url = this.server+url+(url.indexOf('?') == -1? '?':'&')
        +'callback=Gaedj.cb['+Gaedj.addcb(cb)+']'
    this.nload(url);
}
