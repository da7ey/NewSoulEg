import json,re,glob,html,urllib.parse
D=json.load(open('data/exhibitions.json',encoding='utf8'))
CSS='<style>.exh-cta{display:flex;align-items:center;justify-content:space-between;gap:14px 20px;flex-wrap:wrap;background:rgba(139,47,201,.08);border:1px solid rgba(139,47,201,.25);border-right:3px solid var(--purple-bright);border-radius:12px;padding:16px 20px;margin:0 0 24px}.exh-cta p{margin:0;font-weight:700;line-height:1.7;flex:1 1 180px}.exh-cta .btn-primary{padding:11px 22px;font-size:.88rem;white-space:nowrap}.exh-cta-niso{flex:0 0 auto;display:block;width:56px;height:56px;border-radius:50%;overflow:hidden;background:rgba(139,47,201,.2)}.exh-cta-niso img{width:100%;height:100%;object-fit:cover;display:block}.exh-cta a.exh-cta-link{color:var(--purple-glow);font-size:.82rem;text-decoration:underline}</style>'
MARK='<!--exh-cta-->'
n=0
for e in D:
    f=e['page'];t=open(f,encoding='utf8').read()
    t=re.sub(r'<!--exh-cta-->.*?<!--/exh-cta-->','',t,flags=re.S)
    name=html.escape(e['name'],quote=False)
    if e['status']=='confirmed':
        msg=f"عارض في {name} ({e['date_text']})؟ ابدأ تصميم جناحك مع نيو سول واحصل على عرض سعر مجاني."
    else:
        msg=f"بتخطط تشارك في {name}؟ ابدأ تصميم جناحك من دلوقتي واحصل على استشارة وعرض سعر مجاني."
    wa=urllib.parse.quote  # keep readable like existing links
    link=f"https://wa.me/201090235208?text=أريد الاستفسار عن تنفيذ جناح في {e['name']}"
    block=(f'{MARK}{CSS}<div class="exh-cta"><a class="exh-cta-niso" href="https://newsouladv.com/niso-ai-assistant.html" aria-label="نيسو مساعد نيو سول الذكي"><picture><source srcset="https://newsouladv.com/images/niso-mascot.webp" type="image/webp" /><img src="https://newsouladv.com/images/niso-mascot.png" width="64" height="64" alt="نيسو مساعد نيو سول الذكي" loading="lazy" /></picture></a><p>{msg}</p><a href="{html.escape(link,quote=True)}" class="btn-primary" target="_blank" rel="noopener" data-wa-src="exhibition-top">اطلب جناحك في المعرض ده</a>'
           f'<a class="exh-cta-link" href="best-exhibition-companies-egypt.html#our-work">شوف أعمالنا السابقة في المعارض</a></div><!--/exh-cta-->')
    k='<article class="article-content">'
    assert t.count(k)==1,f
    t=t.replace(k,k+block); open(f,'w',encoding='utf8').write(t); n+=1
print(n)
# GA tracking on every page that has gtag
TR='<!--wa-track--><script>document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a[href*=\'wa.me\'],a[href^=\'tel:\']");if(a&&typeof gtag==="function"){gtag("event",a.href.indexOf("tel:")===0?"phone_click":"whatsapp_click",{page_path:location.pathname,link_source:a.getAttribute("data-wa-src")||"page"});}});</script><!--/wa-track-->'
m=0
for f in glob.glob('*.html'):
    t=open(f,encoding='utf8').read()
    if 'gtag(' not in t or '</body>' not in t: continue
    t=re.sub(r'<!--wa-track-->.*?<!--/wa-track-->','',t,flags=re.S)
    i=t.rindex('</body>');t=t[:i]+TR+t[i:]; open(f,'w',encoding='utf8').write(t); m+=1
print(m)
