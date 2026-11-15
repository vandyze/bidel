(function(){
const fa=n=>String(n).replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d]);
const fmt=s=>{s=Math.max(0,Math.floor(s));return fa(Math.floor(s/60)+':'+String(s%60).padStart(2,'0'))};
const P={
song:'<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
poem:'<path d="M20 3C12 4 7 9 6 17"/><path d="M6 17c5-.5 9.5-4 11-9.5"/><path d="M6 17l-2 4"/><path d="M10.5 12h4"/>',
video:'<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M10.5 9.5v5l4-2.5z"/>',
echo:'<circle cx="16.5" cy="12" r="2" fill="currentColor" stroke="none"/><path d="M11.5 8a5.5 5.5 0 0 0 0 8"/><path d="M8 5a10 10 0 0 0 0 14"/>',
chev:'<path d="M14 6l-6 6 6 6"/>',back:'<path d="M5 12h14M13 6l6 6-6 6"/>',
dl:'<path d="M12 4v11"/><path d="M7 10l5 5 5-5"/><path d="M5 20h14"/>',
up:'<path d="M12 16V5"/><path d="M7 10l5-5 5 5"/><path d="M5 20h14"/>',
info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
ext:'<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
home:'<path d="M3 11l9-7 9 7v9a2 2 0 0 1-2 2h-4v-6h-6v6H5a2 2 0 0 1-2-2z"/>',
lib:'<path d="M4 5a2 2 0 0 1 2-2h11v18H6a2 2 0 0 1-2-2zM9 3v18"/>',
search:'<circle cx="11" cy="11" r="7"/><path d="M16 16l4 4"/>',
bm:'<path d="M6 3h12v18l-6-4-6 4z"/>',user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
note:'<path d="M4 20h4l11-11-4-4-11 11z"/><path d="M14 5l4 4"/>',
copy:'<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/>',
share:'<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>',
x:'<path d="M6 6l12 12M18 6L6 18"/>',plus:'<path d="M12 5v14M5 12h14"/>',
narr:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
cred:'<circle cx="9" cy="8" r="3.5"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14.5a6 6 0 0 1 3 5.5"/>',
terj:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/>',
zand:'<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>',
kw:'<path d="M12 3l2.5 6 6.5.5-5 4.5 1.5 6.5L12 17l-5.5 3.5L8 14 3 9.5l6.5-.5z"/>'
};
const ic=k=>'<svg class="i" viewBox="0 0 24 24">'+P[k]+'</svg>';
const PLAY='<svg class="i-play" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
const PAUSE='<svg class="i-pause" viewBox="0 0 24 24"><rect x="6.5" y="5" width="4" height="14" rx="1"/><rect x="13.5" y="5" width="4" height="14" rx="1"/></svg>';
const ALERT='<svg class="i-alert" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5"/><path d="M12 16.5h.01"/></svg>';
const LAB={song:'آهنگ',poem:'سروده',video:'ویدیو'};

const V={
a:['دل اگر بشکند، آینه را غباری نیست','شکست ماست که در عرض هستی پیداست'],
b:['آیینه را تماشا کن، که در تماشای آن','از خود برون می‌روی و در خود می‌رسی'],
c:['رنگ از این کارگه آینه بیرون رفت','تا که بی‌رنگ نگاهی به حقیقت دیدند'],
d:['چو شمع از سر دل سوختیم تا دیدیم','که در محیط فنا قطره‌ای نمی‌ماند'],
e:['بیدل، به دل آرام ندارم چه کنم','از خود به کجا روم، که با خود همراهم']};
const POEM=[['از آینه پرسیدم این نقش ز کیست','گفتا نفسی بود که در خویش گریست'],['هر سو که دویدم به تماشای جهان','دیدم که جهان جز نفسی رفته نیست'],['بشکست دلم، غبار بر آینه نیست','این نقش شکست است که در ما پیداست'],['بیدل به من آموخت که حیرت هنر است','وین شیشه‌ی دل را به نگاهی بشکست']];
const NARR=['این آهنگ از یک شب خواندن غزل ۵۶۷ شروع شد. بیت ششم، که شکستن دل را نه عیب آینه که نشانه‌ی هستی می‌داند، چند هفته در ذهنم ماند تا ملودی‌اش پیدا شد.','ساز اصلی تار است و ضرب آرام آن از وزن خود بیت گرفته شده. در ویدیو، تصویرها همان مسیری را می‌روند که بیت می‌رود: از آینه به شکست، و از شکست به پیدایی.'];
const CRED=[['آهنگساز','آرش رحیمی'],['خواننده','نیلوفر کاظمی'],['تنظیم','بهراد نوری'],['تار','سامان فرهی']];
const W={
all:{title:'شکست ما پیداست',ref:{k:'beit',lab:'غزل ۵۶۷، بیت ۶',v:V.a},cover:1,audio:{dur:252},video:1,poem:POEM,narr:NARR,cred:CRED,date:'۲ مهر ۱۴۰۵'},
poem:{title:'غبار آینه',ref:{k:'beit',lab:'غزل ۸۹۱، بیت ۳',v:V.b},poem:POEM,date:'۱۸ شهریور ۱۴۰۵'},
song:{title:'بی‌رنگ',ref:{k:'ghazal',lab:'غزل ۳۴۵',v:V.c},cover:1,audio:{dur:228},cred:CRED.slice(0,3),date:'۵ شهریور ۱۴۰۵'},
songvid:{title:'حیرت، بند هفتم',ref:{k:'band',lab:'ترجیع‌بند، بند ۷',v:V.d},cover:1,audio:{dur:301},video:1,cred:CRED,date:'۲۰ مرداد ۱۴۰۵'},
long:{title:'شبانه‌ای برای آینه‌ای که نفس را از یاد برد و در حیرت ماند',ref:{k:'beit',lab:'غزل ۱۰۲۳، بیت ۲',v:V.e},audio:{dur:196},date:'۱ مرداد ۱۴۰۵'},
vidonly:{title:'محیط فنا',ref:{k:'beit',lab:'غزل ۲۳۴، بیت ۱',v:V.d},video:1,date:'۱۲ تیر ۱۴۰۵'}
};
const types=w=>['song','video','poem'].filter(t=>t==='song'?w.audio:t==='video'?w.video:w.poem);
const badges=(w,mode)=>'<div class="pj-bds'+(mode==='ic'?' ic':'')+'">'+types(w).map(t=>'<span class="pj-bd" title="'+LAB[t]+'">'+ic(t)+'<span>'+LAB[t]+'</span></span>').join('')+'</div>';
function cover(w,s,force){
  const sm=s<72?' sm':s<120?' md':'';
  if(w.cover&&!force) return '<div class="pj-cov img'+sm+'" style="--s:'+s+'px"><span>cover 1:1</span></div>';
  const t=force||(w.audio?'song':w.video?'video':'poem');
  return '<div class="pj-cov d-'+t+sm+'" style="--s:'+s+'px"><span class="pj-cov-ic">'+ic(t)+'</span><span class="pj-cov-w">'+w.title+'</span><span class="pj-cov-k">پژواک · '+LAB[t]+'</span></div>';
}
function player(dur,o){o=o||{};const st=o.state||'ready',cur=o.cur||0,pct=cur/dur*100;
  return '<div class="pl'+(o.cm?' cm':'')+'" data-state="'+st+'" data-dur="'+dur+'" data-cur="'+cur+'"'+(o.err?' data-err="1"':'')+'>'+
  '<button class="pl-btn" aria-label="پخش">'+PLAY+PAUSE+'<i class="pl-spin"></i>'+ALERT+'</button>'+
  '<div class="pl-mid"><div class="pl-bar" role="slider" aria-label="پیشرفت"><div class="pl-trk"><div class="pl-fill" style="width:'+pct+'%"></div></div><div class="pl-th" style="left:'+pct+'%"></div></div>'+
  '<div class="pl-t"><span class="pl-cur">'+fmt(cur)+'</span><span class="pl-ld">در حال بارگذاری…</span><span class="pl-err">فایل صوتی در دسترس نیست</span><span class="pl-dur">'+fmt(dur)+'</span></div></div></div>';
}
const playerCard=(dur,o)=>'<div class="pl-card'+(o&&o.state==='error'?' err':'')+'">'+player(dur,o)+'<a href="#" class="pl-dl">'+ic('dl')+'<span>دانلود فایل صوتی</span></a></div>';
const refKick=r=>r.k==='ghazal'?r.lab+' · مطلع غزل':r.lab;
const goTxt={beit:'رفتن به این بیت در غزل',ghazal:'خواندن غزل',band:'خواندن بند'};
const beit=(r,noGo)=>'<a href="#" class="pj-beit"><div class="pj-beit-k">الهام از بیدل <span>· '+refKick(r)+'</span></div><div class="pj-beit-m">'+r.v[0]+'</div><div class="pj-beit-m s2">'+r.v[1]+'</div>'+(noGo?'<div style="height:10px"></div>':'<div class="pj-beit-go">'+goTxt[r.k]+ic('chev')+'</div>')+'</a>';
function homeCard(w,o){o=o||{};
  const top='<div class="pj-hc-top">'+cover(w,84)+'<div class="pj-hc-bd">'+badges(w)+'<div class="pj-hc-t">'+w.title+'</div><div class="pj-hc-v">'+w.ref.v[0]+'</div><div class="pj-hc-r">از بیدل · '+w.ref.lab+'</div></div>'+(w.audio?'':'<span class="pj-chev">'+ic('chev')+'</span>')+'</div>';
  return w.audio?'<div class="pj-hc"><a href="#" class="pj-hc-lnk">'+top+'</a>'+player(w.audio.dur,Object.assign({cm:1},o))+'</div>':'<a href="#" class="pj-hc">'+top+'</a>';
}
const homeBlock=(w,o)=>'<div class="pj-shd"><span class="section-h">تازه‌ترین پژواک</span><a href="#">همه‌ی پژواک‌ها'+ic('chev')+'</a></div>'+homeCard(w,o);
const row=w=>'<a href="#" class="pj-row" data-types="'+types(w).join(' ')+'">'+cover(w,64)+'<div class="pj-row-bd"><div class="pj-row-t">'+w.title+'</div><div class="pj-row-r">'+w.ref.lab+'</div><div class="pj-row-m">'+badges(w,types(w).length>2?'ic':'')+'<span class="pj-row-d">'+w.date+'</span></div></div></a>';
const feat=w=>'<a href="#" class="pj-feat">'+cover(w,112)+'<div class="pj-row-bd"><div class="pj-row-t">'+w.title+'</div><div class="pj-feat-v"><div>'+w.ref.v[0]+'</div><div>'+w.ref.v[1]+'</div></div><div class="pj-row-r">'+w.ref.lab+'</div><div class="pj-row-m">'+badges(w)+'<span class="pj-row-d">'+w.date+'</span></div></div></a>';
const tile=w=>'<a href="#" class="pj-tile">'+cover(w,300)+'<div class="pj-tile-bd"><div class="pj-row-t">'+w.title+'</div><div class="pj-feat-v"><div>'+w.ref.v[0]+'</div></div><div class="pj-row-r">'+w.ref.lab+'</div><div class="pj-row-m">'+badges(w)+'<span class="pj-row-d">'+w.date+'</span></div></div></a>';
const video=o=>'<div class="pj-vid"><div class="pj-vid-f'+(o&&o.blocked?' blocked':'')+'"><span class="pj-vid-p"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></span><span>'+(o&&o.blocked?'YouTube embed · not loaded':'YouTube embed · 16:9')+'</span></div><div class="pj-vid-n">'+ic('info')+'<span>در صورت عدم نمایش، از فیلترشکن استفاده کنید</span><a href="#">تماشا در یوتیوب'+ic('ext')+'</a></div></div>';
const poemBox=p=>'<div class="pj-poem"><div class="pj-poem-k">'+ic('poem')+'سروده‌ی تازه</div>'+p.map(c=>'<div class="pj-poem-c"><div>'+c[0]+'</div><div>'+c[1]+'</div></div>').join('')+'<div class="pj-poem-n">این شعر سروده‌ی صاحب بیدلی است، با الهام از بیت بالا؛ از بیدل نیست.</div></div>';
const sh=(k,t,c)=>'<div class="pj-sh">'+ic(k)+t+(c?'<span class="cnt">'+c+'</span>':'')+'</div>';
const cred=c=>'<dl class="pj-cred">'+c.map(r=>'<div><dt>'+r[0]+'</dt><dd>'+r[1]+'</dd></div>').join('')+'</dl>';
function detailParts(w,o){o=o||{};
  const head='<div class="pj-dh">'+cover(w,o.cs||(w.cover?220:152))+'<h1 class="pj-dt">'+w.title+'</h1><div class="pj-dm">'+badges(w)+'<span>'+w.date+'</span></div></div>';
  const aud=w.audio?'<div class="pj-gap">'+playerCard(w.audio.dur,o.pl)+'</div>':'';
  const vid=w.video?'<div class="pj-gap">'+video()+'</div>':'';
  const po=w.poem?sh('poem','متن سروده')+poemBox(w.poem):'';
  const na=w.narr?sh('narr','روایت')+'<div class="pj-narr">'+w.narr.map(p=>'<p>'+p+'</p>').join('')+'</div>':'';
  const cr=w.cred?sh('cred','همکاران')+cred(w.cred):'';
  return {head,beit:beit(w.ref),aud,vid,po,na,cr};
}
function detail(w,o){const d=detailParts(w,o);return d.head+d.beit+d.aud+d.vid+d.po+d.na+d.cr}
function nav(tab){const it=(k,t,l)=>'<button class="bn-item'+(tab===k?' on':'')+'"><span class="bn-ic"><svg viewBox="0 0 24 24">'+P[t]+'</svg></span><span class="bn-lab">'+l+'</span></button>';
  return '<nav class="bn">'+it('home','home','خانه')+it('browse','lib','کتابخانه')+'<div class="bn-fab"><button class="bn-item bn-c"><span class="bn-ic"><svg viewBox="0 0 24 24">'+P.search+'</svg></span><span class="bn-lab">کاوش</span></button></div>'+it('bm','bm','نشان‌ها')+it('profile','user','حساب')+'</nav>';}
function phone(o){
  return '<div class="ph" style="width:'+(o.w||390)+'px;'+(o.h?'height:'+o.h+'px':'')+'"><header class="hd">'+(o.back===false?'':'<button class="hd-back" aria-label="بازگشت">'+ic('back')+'</button>')+'<div class="hd-logo"><img src="assets/logo-mark.png" alt=""></div><div class="hd-title"><div class="hd-t1">'+o.title+'</div>'+(o.sub?'<div class="hd-t2">'+o.sub+'</div>':'')+'</div></header>'+(o.pre||'')+'<div class="ct">'+o.body+'</div>'+nav(o.tab||'browse')+(o.overlay||'')+'</div>';
}
function cp(v,n,o){o=o||{};
  let h='<div class="cp'+(o.open?' open':'')+'"><span class="cn">'+fa(n)+'</span>';
  if(o.mk) h+='<button class="pj-mk'+(o.on?' on':'')+'" data-sheet="'+(o.sid||'')+'" aria-label="پژواک‌های این بیت">'+ic('echo')+(o.mk>1?'<b>'+fa(o.mk)+'</b>':'')+'</button>';
  h+='<div class="ms">'+v[0]+'</div><div class="ms s2">'+v[1]+'</div>';
  if(o.open) h+='<div class="ca"><button>'+ic('bm')+'نشان</button><button>'+ic('note')+'یادداشت</button><button>'+ic('share')+'اشتراک</button><button>'+ic('copy')+'رونوشت</button></div>';
  return h+'</div>';
}
const banner=(t,s)=>'<a href="#" class="pj-bn"><span class="pj-bn-ic">'+ic('echo')+'</span><span class="pj-bn-tx"><div class="pj-bn-t">'+t+'</div>'+(s?'<div class="pj-bn-s">'+s+'</div>':'')+'</span><span class="pj-chev">'+ic('chev')+'</span></a>';
function sheet(v,ref,list,open,id){
  return '<div class="ms-bg'+(open?' open':'')+'" data-id="'+(id||'')+'"><div class="ms-sheet"><div class="ms-grip"></div><div class="ms-h"><span class="ms-dot">'+ic('echo')+'</span><div class="ms-h-tx"><div class="ms-h-name">پژواک‌های این بیت</div><div class="ms-h-sub">'+fa(list.length)+' اثر الهام‌گرفته از این بیت</div></div><button class="ms-x" aria-label="بستن">'+ic('x')+'</button></div>'+beit({k:'beit',lab:ref,v},true)+'<div class="pj-list">'+list.map(row).join('')+'</div></div></div>';
}
const empty=()=>'<div class="pj-empty"><div class="pj-rings"><i></i><i></i><i></i><b>'+ic('echo')+'</b></div><h3>هنوز پژواکی منتشر نشده</h3><p>اینجا جای سروده‌ها، آهنگ‌ها و ویدیوهایی است که هر کدام از یک بیت یا غزل بیدل برخاسته‌اند.</p><a href="#" class="pj-btn">خواندن غزلیات'+ic('chev')+'</a></div>';
const notFound=()=>'<div class="pj-empty"><div class="pj-rings lost"><i></i><i></i><i></i><b>'+ic('echo')+'</b></div><h3>این پژواک یافت نشد</h3><p>ممکن است نشانی نادرست باشد یا این اثر دیگر در دسترس نباشد.</p><a href="#" class="pj-btn">بازگشت به پژواک‌ها'+ic('chev')+'</a><a href="#" class="pj-btn gh">صفحه‌ی اصلی</a></div>';
const loader=m=>'<div class="book-loading"><div class="book-loader"><span></span><span></span><span></span></div><div class="book-loading-msg">'+(m||'در حال آوردن پژواک…')+'</div></div>';
Object.assign(window,{PJ:{fa,fmt,ic,P,LAB,V,W,POEM,CRED,types,badges,cover,player,playerCard,beit,homeCard,homeBlock,row,feat,tile,video,poemBox,sh,cred,detail,detailParts,nav,phone,cp,banner,sheet,empty,notFound,loader}});
})();
