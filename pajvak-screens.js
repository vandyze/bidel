(function(){
const J=window.PJ,{ic,W,V,fa}=J;
const LEAD='<p class="pj-lead">سروده‌ها، آهنگ‌ها و ویدیوهایی که هر کدام از یک بیت یا غزل بیدل برخاسته‌اند.</p>';
const list3=[W.all,W.poem,W.song];
const pool=['نفس رفته','کارگاه آینه','زنگار','ناله‌ی بی‌نام','سفر آینه','حجاب بینش','پرواز نظر','شکست ساغر','فضای تنگ','دو سو','یک نگاه','آینه‌ی وحدت'];
const vv=[V.a,V.b,V.c,V.d,V.e];
const mo=['شهریور','مرداد','تیر','خرداد','اردیبهشت','فروردین','اسفند','بهمن','دی'];
const many=pool.map((t,i)=>({title:t,ref:{k:'beit',lab:'غزل '+fa(120+i*211)+'، بیت '+fa(i%7+1),v:vv[i%5]},cover:i%3===0,audio:i%4!==1?{dur:200}:0,video:i%3===2,poem:i%4===1||i%5===0?[1]:0,date:fa(28-i*2)+' '+mo[Math.min(8,i)]+(i<6?' ۱۴۰۵':' ۱۴۰۴'),y:i<6?'۱۴۰۵':'۱۴۰۴'}));
function manyList(){
  let h='<div class="pj-seg"><button class="on" data-f="">همه</button><button data-f="song">'+ic('song')+'آهنگ</button><button data-f="poem">'+ic('poem')+'سروده</button><button data-f="video">'+ic('video')+'ویدیو</button></div><div class="pj-list">'+J.feat(W.all);
  let y='';many.forEach(w=>{if(w.y!==y){y=w.y;h+='<div class="pj-yr">'+y+'<span>'+(y==='۱۴۰۵'?'۲۶ اثر':'۲۴ اثر')+'</span></div>'}h+=J.row(w)});
  return h+'</div>';
}
const ghost=(t,h)=>'<div class="ghost" style="height:'+h+'px">'+t+'</div>';
const homeBody=o=>'<div class="home-search">'+ic('search')+'<span>جستجو در دیوان…</span></div>'+ghost('هیرو / سلوک من<br>بدون تغییر',110)+ghost('هفت گام · بیت امروز در گام ۱<br>بدون تغییر',150)+J.homeBlock(W.all,o)+'<div class="section-h" style="margin:6px 4px 10px">کلمات کلیدی امروز</div>'+ghost('نوار کلمات کلیدی · بدون تغییر',84);
const libItems=[['غزلیات','متن کاملِ غزلیات بیدل دهلوی.','۲۸۲۷ غزل'],['ترجیع‌بند','ترجیع‌بندِ حیرت، بند به بند.','۳۴ بند · حیرت'],['زند بیدل','شرح و تحلیلِ سراسرِ دیوان.','شرح شروین وکیلی'],['خوانش‌ها','خوانش‌های تفسیری، بند به بند.','تفسیر و شرحِ ترجیع‌بند'],['پژواک‌ها','سروده، آهنگ و ویدیوهایی که از شعر بیدل الهام گرفته‌اند.','۳ اثر']];
const libBody='<div class="lib">'+libItems.map(i=>'<a href="#" class="lib-card"><div class="lib-bd"><div class="lib-t">'+i[0]+'</div><div class="lib-d">'+i[1]+'</div><div class="lib-s">'+i[2]+'</div></div><span class="lib-ar">'+ic('chev')+'</span></a>').join('')+'</div>';
const listPh=(body,o)=>J.phone(Object.assign({title:'پژواک',sub:'آثار الهام‌گرفته از بیدل',body},o||{}));
const featList=l=>LEAD+'<div class="pj-list">'+l.map(J.feat).join('')+'</div><div class="pj-end">پژواک‌های تازه به‌مرور افزوده می‌شوند</div>';
const detPh=(w,o)=>J.phone(Object.assign({title:'پژواک',sub:w.title,body:J.detail(w,o)},o||{}));
const comp=(items)=>'<div class="comp">'+items.map(i=>'<div class="st-l">'+i[0]+'</div>'+i[1]).join('')+'</div>';
// ghazal
const ghSheets=J.sheet(V.a,'غزل ۵۶۷، بیت ۶',[W.all,W.long],false,'s6')+J.sheet(V.b,'غزل ۵۶۷، بیت ۳',[W.poem],false,'s3');
const ghBody=J.banner('این غزل الهام‌بخش یک سروده شده است','«نفس رفته»')+J.cp(V.d,1)+J.cp(V.e,2)+J.cp(V.b,3,{mk:1,sid:'s3'})+J.cp(V.c,4,{open:1})+J.cp(['چشم بستن چو آینه از خویش، بصیرت است','تا چشم باز است، نظر در حجاب ماست'],5)+J.cp(V.a,6,{mk:2,sid:'s6'});
const ghPre='<div class="subnav"><button>غزل قبل</button><button>غزل بعد</button></div>';
const ghazal=(open)=>J.phone({title:'غزل ۵۶۷',sub:'شکست ساغر',h:900,pre:ghPre,body:open?ghBody.replace('class="pj-mk" data-sheet="s6"','class="pj-mk on" data-sheet="s6"'):ghBody,overlay:open?J.sheet(V.a,'غزل ۵۶۷، بیت ۶',[W.all,W.long],true,'s6')+J.sheet(V.b,'غزل ۵۶۷، بیت ۳',[W.poem],false,'s3'):ghSheets});
const terj=J.phone({title:'ترجیع‌بند',sub:'بند ۷ از ۳۴',h:700,pre:'<div class="subnav"><button>بند قبل</button><button>بند بعد</button></div>',body:J.banner('این بند الهام‌بخش یک آهنگ و ویدیو شده است','«حیرت، بند هفتم»')+J.cp(V.d,1)+J.cp(V.e,2,{mk:1,sid:''})+J.cp(V.b,3)});
// desktop
const sb=on=>'<aside class="sb"><div class="sb-brand"><div class="sb-logo"><img src="assets/logo-mark.png" alt=""></div><div><div class="sb-name">بیدلی</div><div class="sb-sub">دیوان بیدل دهلوی</div></div></div><div class="sb-search">'+ic('search')+'<span>جست‌وجو در دیوان…</span></div><div class="sb-nav"><div class="sb-item">'+ic('home')+'خانه</div><div class="sb-item">'+ic('bm')+'نشان‌ها<span class="n">۲۴</span></div><div class="sb-item">'+ic('kw')+'کلمات کلیدی<span class="n">۳۱۴</span></div></div><div class="sb-group">کتابخانه</div><div class="sb-nav"><div class="sb-item">'+ic('lib')+'غزلیات<span class="n">۲۸۲۷</span></div><div class="sb-item">'+ic('terj')+'ترجیع‌بند<span class="n">۳۴</span></div><div class="sb-item">'+ic('zand')+'زند بیدل</div><div class="sb-item">'+ic('narr')+'خوانش‌ها</div><div class="sb-item on">'+ic('echo')+'پژواک‌ها<span class="n">۳</span></div></div></aside>';
const dkList='<div class="win">'+sb()+'<div class="pane"><div class="tb"><span class="tb-h">پژواک‌ها</span><span class="tb-s">آثار الهام‌گرفته از بیدل</span></div><div class="dk"><div class="dk-h1">پژواک</div>'+LEAD.replace('pj-lead"','pj-lead" style="font-size:14px;margin:0"')+'<div class="dk-grid">'+list3.map(J.tile).join('')+'</div><div class="pj-end" style="margin-top:36px">پژواک‌های تازه به‌مرور افزوده می‌شوند</div></div></div></div>';
const dp=J.detailParts(W.all,{cs:340});
const dkDetail='<div class="win">'+sb()+'<div class="pane"><div class="tb"><span class="tb-crumb">پژواک‌ها'+ic('chev')+'<b style="color:var(--gd)">'+W.all.title+'</b></span></div><div class="dd"><div class="dd-side">'+J.cover(W.all,340)+'<h1 class="pj-dt">'+W.all.title+'</h1><div class="pj-dm">'+J.badges(W.all)+'<span>'+W.all.date+'</span></div>'+J.playerCard(252,{})+J.sh('cred','همکاران').replace('pj-sh"','pj-sh" style="margin:14px 2px 0"')+J.cred(W.all.cred)+'</div><div class="dd-main">'+dp.beit+dp.vid+dp.po+dp.na+'</div></div></div></div>';
// admin
const crRow=(r,n)=>'<div class="af-cr"><select><option>'+r+'</option><option>آهنگساز</option><option>خواننده</option><option>تنظیم</option><option>نوازنده</option></select><input value="'+n+'" placeholder="نام"><button class="af-x" aria-label="حذف">'+ic('x')+'</button></div>';
const admin='<div class="adm"><h3>پژواک تازه</h3>'+
'<div class="af"><label>عنوان<small>تا ۶۰ نویسه · الزامی</small></label><input value="شکست ما پیداست"></div>'+
'<div class="af"><label>مرجع<small>الزامی</small></label><div class="af-seg"><button class="on">بیت</button><button>کل غزل</button><button>بند ترجیع</button></div><div class="af-row"><input value="غزل ۵۶۷"><input value="بیت ۶"></div><div class="af-prev">'+J.beit({k:'beit',lab:'غزل ۵۶۷، بیت ۶',v:V.a},true)+'</div></div>'+
'<div class="af"><label>کاور<small>مربعی ۱:۱ · اختیاری؛ بدون آن، کاور پیش‌فرض</small></label><div class="af-up">'+ic('up')+'<span class="nm">cover-shekast.jpg</span><span>بارگذاری شد</span></div></div>'+
'<div class="af"><label>فایل صوتی<small>اختیاری</small></label><div class="af-up">'+ic('up')+'<span class="nm">shekast-ma-peydast.mp3</span><span>۶۲٪</span></div><div class="af-prog"><span style="width:62%"></span></div><div class="af-pct">۵٫۱ از ۸٫۲ مگابایت</div></div>'+
'<div class="af"><label>ویدیو<small>نشانی یوتیوب · اختیاری</small></label><input dir="ltr" value="https://youtu.be/…"></div>'+
'<div class="af"><label>متن سروده<small>هر بیت در یک خط، مصراع‌ها با «/» جدا</small></label><textarea>از آینه پرسیدم این نقش ز کیست / گفتا نفسی بود که در خویش گریست</textarea></div>'+
'<div class="af"><label>روایت<small>اختیاری</small></label><textarea></textarea></div>'+
'<div class="af"><label>همکاران</label><div class="af-crs">'+crRow('آهنگساز','آرش رحیمی')+crRow('خواننده','نیلوفر کاظمی')+'</div><button class="af-add">'+ic('plus')+'افزودن همکار</button></div>'+
'<div class="af"><label>تاریخ انتشار</label><input value="۲ مهر ۱۴۰۵" style="max-width:220px"></div>'+
'<div class="adm-foot"><button class="pj-btn">انتشار</button><button class="pj-btn gh">ذخیره‌ی پیش‌نویس</button></div></div>';
// spec
const sw=[['--bg','#f0ebde','زمینه'],['--sf','#f7f3e6','کارت / پخش‌کننده'],['--sf2','#fbf8ee','کارت برجسته / سروده'],['--br2','#dcd5be','مرز نرم'],['--gh','#e9eedb','نشان نوع'],['--go','#5a7048','دکمه‌ی پخش / پیشرفت'],['--gd','#3a4830','عنوان / کاور ویدیو'],['--mu','#6a7a5a','متن کمرنگ'],['--sah','#f4ebd0','کارت بیت / بنر'],['--sa','#c89030','نشانه‌ی پژواک'],['--sa2','#a87420','مرجع بیت'],['--er','#a04030','خطای صوت']];
const tt=(rows)=>'<table class="tt">'+rows.map(r=>'<tr><td>'+r[0]+'</td><td>'+r[1]+'</td><td class="m">'+r[2]+'</td></tr>').join('')+'</table>';
const icBox=(k,t,n)=>'<div><span class="ics">'+ic(k)+ic(k)+'</span>'+t+'<small>'+n+'</small></div>';
const spec='<div class="spec"><div class="sp-grid">'+
'<div class="sp-full"><h3>تصمیم‌ها</h3><div class="dec">'+
'<div><b>جهت نوار پیشرفت: چپ‌به‌راست.</b> کل پخش‌کننده یک واحد LTR است: دکمه چپ، زمان سپری‌شده چپ، زمان کل راست. زمان متن نیست و کاربر همین جهت را از هر پخش‌کننده‌ی دیگری می‌شناسد. برچسب‌ها و پیام خطا فارسی و راست‌به‌چپ می‌مانند.</div>'+
'<div><b>تفکیک دو شعر.</b> بیت بیدل همیشه در کارت زعفرانیِ خوانش‌ها، با مصراع دوم پلکانی و برچسب «الهام از بیدل». سروده‌ی تازه همیشه در قاب کامل روشن، مصراع‌ها وسط‌چین، رنگ سبز، برچسب «سروده‌ی تازه» و یادداشت پایانی. رنگ، چیدمان و برچسب هر سه متفاوت‌اند.</div>'+
'<div><b>جای کارت در خانه:</b> پس از «هفت گام» و پیش از «کلمات کلیدی امروز». بیت امروز نخستین دعوت به خواندن می‌ماند و پژواک پس از آن می‌آید.</div>'+
'<div><b>تاریخ</b> به‌جای انتهای صفحه، زیر عنوان و کنار نشان‌های نوع آمده؛ یک بار، در جایی که پیش از خواندن دیده می‌شود.</div>'+
'<div><b>لیست:</b> تا ۳ اثر، کارت بزرگ با بیت الهام‌بخش. بیشتر از آن، تازه‌ترین بزرگ و بقیه ردیف فشرده با جداکننده‌ی سال. از ۸ اثر به بعد فیلتر نوع ظاهر می‌شود.</div>'+
'<div><b>نشانه‌ی بیت</b> در ستون شماره‌ی بیت و زیر آن می‌نشیند؛ دور از ردیف نشان/یادداشت/اشتراک/رونوشت که با باز شدن بیت پایینش می‌آید. ناحیه‌ی لمس ۴۴px با حاشیه‌ی نامرئی.</div>'+
'<div><b>آینده:</b> پخش‌کننده‌ی سراسری همان نسخه‌ی فشرده است که می‌تواند بالای Bottom Navigation بنشیند؛ بوکمارک جای خود را کنار نشان‌های سرصفحه‌ی جزئیات دارد؛ نظرات پس از «همکاران».</div>'+
'<div><b>رنگ تازه‌ای اضافه نشده.</b> زعفرانی موجود نشانه‌ی بیدل و پژواک است و سبز زیتونی کنترل‌ها.</div></div></div>'+
'<div class="sp-full"><h3>رنگ‌ها (پالت فعلی)</h3><div class="sw" style="grid-template-columns:repeat(6,minmax(0,1fr))">'+sw.map(s=>'<div><i style="background:'+s[1]+'"></i><b>'+s[2]+'</b><span>'+s[0]+' '+s[1]+'</span></div>').join('')+'</div></div>'+
'<div><h3>تایپوگرافی · IRANYekanX</h3>'+tt([['عنوان جزئیات','۲۳ / ExtraBold','23px 800 1.45'],['عنوان کارت ویژه','۱۶٫۵ / Bold','16.5px 700 1.5'],['عنوان ردیف / کارت خانه','۱۵–۱۶ / Bold','15–16px 700 1.5'],['بیت بیدل','۱۷ / Medium','17px 500 2.0'],['سروده‌ی تازه','۱۶٫۵ / Regular','16.5px 400 1.95'],['روایت','۱۵٫۵ / Regular','15.5px 400 2.05'],['سرفصل بخش','۱۳ / Bold','13px 700'],['مرجع / متا','۱۱–۱۲','11–12px 600'],['زمان پخش','۱۱٫۵ tabular','11.5px tnum']])+'</div>'+
'<div><h3>فاصله و گوشه</h3>'+tt([['حاشیه‌ی صفحه','۱۴','14px'],['پدینگ کارت','۱۲ / ردیف ۱۰','12px / 10px'],['فاصله‌ی کارت‌ها','۱۰','10px'],['فاصله‌ی بخش‌ها','۲۸ بالا · ۱۲ پایین','28px / 12px'],['گوشه‌ی کارت','۱۶ / ردیف ۱۴','16px / 14px'],['گوشه‌ی کاور','۱۱٪ اندازه','calc(s*.11)'],['دکمه‌ی پخش','۵۲ کامل / ۴۴ فشرده','52px / 44px'],['نوار پیشرفت','ضخامت ۴ · ناحیه‌ی لمس ۲۶','4px / 26px'],['حداقل لمس','۴۴','44px']])+'</div>'+
'<div><h3>آیکن‌ها · ۲۴ و ۱۶ · خط ۱٫۷</h3><div class="icg">'+icBox('song','آهنگ','song')+icBox('poem','سروده','poem')+icBox('video','ویدیو','video')+icBox('echo','نشانه‌ی پژواک','echo')+'</div><div style="margin-top:16px;display:flex;gap:20px;align-items:center">'+J.badges(W.all)+J.badges(W.all,'ic')+'</div></div>'+
'<div><h3>کاورهای پیش‌فرض</h3><div class="covg">'+['song','poem','video'].map(t=>'<figure>'+J.cover({title:t==='song'?'بی‌رنگ':t==='poem'?'غبار آینه':'محیط فنا'},150,t)+'<figcaption>'+J.LAB[t]+'</figcaption></figure>').join('')+'<figure>'+['song','poem','video'].map(t=>J.cover({title:''},56,t)).join('<div style="height:6px"></div>')+'<figcaption>≤۷۲px</figcaption></figure></div><p style="font-size:12px;color:var(--mu);line-height:1.9;margin-top:12px">نوع اصلی: آهنگ اگر صوت دارد، وگرنه ویدیو، وگرنه سروده. آهنگ: حلقه‌های پژواک؛ سروده: کاغذ خط‌دار؛ ویدیو: قاب تیره. عنوان خود اثر نقش اصلی است؛ در اندازه‌های کوچک فقط آیکن نوع.</p></div>'+
'</div></div>';
const mkDemo='<div class="sp-demo">'+J.cp(V.b,3,{mk:1})+'</div>';
const ROWS=[
{n:'پژواک · bideli.ir',t:'طراحی بخش پژواک',d:'همه‌ی فریم‌ها در همین سند، با پالت و فونت فعلی سایت. پخش‌کننده‌ها، نشانه‌های بیت، فیلتر لیست و فرم ادمین قابل کلیک‌اند. متن‌های بیت و سروده نمونه‌اند.',f:[['مشخصات','رنگ، تایپ، فاصله، آیکن، کاور و تصمیم‌ها',spec]]},
{n:'۰۱',t:'صفحه‌ی اصلی و کتابخانه',d:'کارت «تازه‌ترین پژواک» پس از هفت گام؛ پخش از همان کارت. در کتابخانه، «پژواک‌ها» با همان کارت‌های موجود.',f:[
 ['خانه · ۳۹۰','بخش‌های خط‌چین بدون تغییرند',J.phone({title:'بیدلی',back:false,tab:'home',body:homeBody()})],
 ['خانه · ۳۶۰','در حال پخش',J.phone({w:360,title:'بیدلی',back:false,tab:'home',body:homeBody({state:'paused',cur:84})})],
 ['کتابخانه · ۳۹۰','آیتم پنجم',J.phone({title:'کتابخانه',sub:'متن کاملِ دیوان',body:libBody})],
 ['کارت خانه · حالت‌ها','',comp([['با صوت · آماده',J.homeCard(W.all)],['با صوت · در حال پخش',J.homeCard(W.song,{state:'playing',cur:61})],['بدون صوت · کل کارت لینک است',J.homeCard(W.poem)],['بدون کاور + عنوان ۶۰ نویسه',J.homeCard(W.long)],['خطای صوت',J.homeCard(W.song,{state:'error'})]])]
]},
{n:'۰۲',t:'لیست /pajvak',d:'با کم‌ترین تعداد، کارت‌های بزرگ با بیت؛ با تعداد زیاد، ردیف فشرده، جداکننده‌ی سال و فیلتر.',f:[
 ['۱ اثر','شروع کار',listPh(featList([W.all]))],
 ['۳ اثر','',listPh(featList(list3))],
 ['۵۰ اثر','فیلتر قابل کلیک است',listPh(LEAD.replace('برخاسته‌اند.','برخاسته‌اند. ۵۰ اثر.')+manyList(),{h:1000})],
 ['۳ اثر · ۳۶۰','',listPh(featList(list3),{w:360})],
 ['لیست خالی','',listPh(J.empty(),{h:760})],
 ['در حال بارگذاری','لودر کتابی موجود',listPh(J.loader('در حال آوردن پژواک‌ها…'),{h:760})],
 ['۴۰۴','',J.phone({title:'پژواک',body:J.notFound(),h:760})]
]},
{n:'۰۳',t:'جزئیات /pajvak/{slug}',d:'ترتیب: کاور و عنوان (با نوع و تاریخ)، بیت بیدل، صوت، ویدیو، سروده، روایت، همکاران. هر بخش فقط وقتی فیلدش پر است.',f:[
 ['فقط سروده','بدون کاور و صوت · کاور پیش‌فرض',detPh(W.poem)],
 ['فقط آهنگ','کاور، صوت، همکاران · مرجع کل غزل',detPh(W.song)],
 ['آهنگ + ویدیو','مرجع بند ترجیع',detPh(W.songvid,{pl:{state:'paused',cur:112}})],
 ['همه‌ی فیلدها · ۳۹۰','',detPh(W.all)],
 ['همه‌ی فیلدها · ۳۶۰','',detPh(W.all,{w:360})]
]},
{n:'۰۴',t:'پخش‌کننده و ویدیو',d:'دو اندازه، پنج حالت. نوار پیشرفت چپ‌به‌راست و قابل کشیدن؛ هر کدام را امتحان کنید.',f:[
 ['پخش‌کننده‌ی کامل','',comp([['آماده',J.playerCard(252)],['در حال بارگذاری',J.playerCard(252,{state:'loading'})],['در حال پخش',J.playerCard(252,{state:'playing',cur:97})],['متوقف',J.playerCard(252,{state:'paused',cur:97})],['خطا',J.playerCard(252,{state:'error'})]])],
 ['پخش‌کننده‌ی فشرده','داخل کارت خانه',comp([['آماده',J.player(228,{cm:1})],['در حال بارگذاری',J.player(228,{cm:1,state:'loading'})],['در حال پخش',J.player(228,{cm:1,state:'playing',cur:61})],['متوقف',J.player(228,{cm:1,state:'paused',cur:61})],['خطا',J.player(228,{cm:1,state:'error'})]])],
 ['بلوک ویدیو','پیام همیشه دیده می‌شود',comp([['embed بارگذاری‌شده',J.video()],['embed بارگذاری نشده',J.video({blocked:1})]])]
]},
{n:'۰۵',t:'غزل و ترجیع',d:'نشانه‌ی ظریف در ستون شماره‌ی بیت، با عدد برای چند پژواک. بنر زیر عنوان برای پژواکِ کل غزل یا بند. روی نشانه‌ها بزنید.',f:[
 ['صفحه‌ی غزل','بیت ۳: یک پژواک · بیت ۶: دو پژواک · بیت ۴ باز',ghazal(false)],
 ['Bottom Sheet','پژواک‌های بیت ۶',ghazal(true)],
 ['بند ترجیع','بنر برای کل بند',terj],
 ['نشانه و بنر · حالت‌ها','',comp([['نشانه · یک پژواک',mkDemo],['نشانه · چند پژواک',mkDemo.replace('</svg></button>','</svg><b>۳</b></button>')],['نشانه · فشرده/باز',mkDemo.replace('class="pj-mk"','class="pj-mk on"')],['بنر · یک اثر',J.banner('این غزل الهام‌بخش یک آهنگ شده است','«بی‌رنگ»')],['بنر · سروده',J.banner('این غزل الهام‌بخش یک سروده شده است','«غبار آینه»')],['بنر · چند اثر (Bottom Sheet باز می‌شود)',J.banner('این غزل الهام‌بخش ۲ پژواک شده است','«بی‌رنگ» و «غبار آینه»')]])]
]},
{n:'۰۶',t:'دسکتاپ',d:'همان کامپوننت‌ها در قاب دسکتاپ فعلی. در جزئیات، کاور و پخش‌کننده ثابت در ستون کناری، متن‌ها در ستون خواندن.',f:[['لیست · ۱۴۴۰','',dkList],['جزئیات · ۱۴۴۰','',dkDetail]]},
{n:'۰۷',t:'پنل ادمین',d:'فرم کاربردی؛ مرجع با پیش‌نمایش بیت، آپلود با پیشرفت، همکاران پویا.',f:[['تب پژواک','',admin]]}
];
let html='';
if(window.__ROW!=null){const k=ROWS[window.__ROW];ROWS.length=0;ROWS.push(k)}
ROWS.forEach((r,ri)=>{html+='<div class="rowlab" data-r="'+ri+'"><div class="n">'+r.n+'</div><h2>'+r.t+'</h2><p>'+r.d+'</p></div>';r.f.forEach(f=>{html+='<div class="frame" data-r="'+ri+'"><div class="flabel">'+f[0]+(f[1]?'<span>'+f[1]+'</span>':'')+'</div>'+f[2]+'</div>'})});
document.body.insertAdjacentHTML('beforeend',html);
function layout(){
  const GAP=64,RG=160,X0=80;const rows=ROWS.map((_,ri)=>[...document.querySelectorAll('.frame[data-r="'+ri+'"]')]);
  rows.flat().forEach(f=>{f.style.width=f.lastElementChild.offsetWidth+'px'});
  const maxW=Math.max(...rows.map(fs=>fs.reduce((a,f)=>a+f.offsetWidth,0)+GAP*(fs.length-1)));
  const right=X0+Math.max(maxW,1100);let y=80;
  rows.forEach((fs,ri)=>{const lab=document.querySelector('.rowlab[data-r="'+ri+'"]');lab.style.left=(right-1100)+'px';lab.style.top=y+'px';y+=lab.offsetHeight+36;let x=right,h=0;fs.forEach(f=>{x-=f.offsetWidth;f.style.left=x+'px';f.style.top=y+'px';x-=GAP;h=Math.max(h,f.offsetHeight)});y+=h+RG});
}
(document.fonts?document.fonts.ready:Promise.resolve()).then(layout);layout();
// interactions
document.addEventListener('click',e=>{
  const a=e.target.closest('a[href="#"]');
  const btn=e.target.closest('.pl-btn');
  if(btn){e.preventDefault();e.stopPropagation();toggle(btn.closest('.pl'));return}
  const mk=e.target.closest('.pj-mk');
  if(mk&&mk.dataset.sheet){const ph=mk.closest('.ph');const s=ph&&ph.querySelector('.ms-bg[data-id="'+mk.dataset.sheet+'"]');if(s){s.classList.add('open');mk.classList.add('on')}return}
  const bg=e.target.closest('.ms-bg');
  if(bg&&(e.target===bg||e.target.closest('.ms-x'))){bg.classList.remove('open');bg.closest('.ph').querySelectorAll('.pj-mk.on').forEach(m=>m.classList.remove('on'));return}
  const sg=e.target.closest('.pj-seg button');
  if(sg){const seg=sg.parentNode;seg.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b===sg));const f=sg.dataset.f;const lst=seg.nextElementSibling;lst.querySelectorAll('.pj-row,.pj-feat').forEach(r=>{const t=r.dataset.types||'song video poem';r.style.display=!f||t.indexOf(f)>-1?'':'none'});return}
  const as=e.target.closest('.af-seg button');
  if(as){as.parentNode.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b===as));return}
  const ax=e.target.closest('.af-x');if(ax){ax.parentNode.remove();return}
  const ad=e.target.closest('.af-add');if(ad){ad.previousElementSibling.insertAdjacentHTML('beforeend',crRow('نوازنده',''));layout();return}
  if(a)e.preventDefault();
});
const upd=el=>{const d=+el.dataset.dur,c=+el.dataset.cur,p=Math.min(100,c/d*100);el.querySelector('.pl-fill').style.width=p+'%';el.querySelector('.pl-th').style.left=p+'%';el.querySelector('.pl-cur').textContent=J.fmt(c)};
function play(el){document.querySelectorAll('.pl').forEach(p=>{if(p!==el&&p._live){p.dataset.state='paused';p._live=false}});el.dataset.state='playing';el._live=true;if(!tick)tick=setInterval(step,250)}
let tick=null;
function toggle(el){const st=el.dataset.state;if(st==='error'||st==='loading')return;
  if(st==='playing'){el.dataset.state='paused';el._live=false;return}
  el._loaded=el._loaded||st==='paused';
  if(!el._loaded){el.dataset.state='loading';setTimeout(()=>{el._loaded=true;play(el)},900)}else play(el)}
function step(){let any=false;document.querySelectorAll('.pl[data-state=playing]').forEach(el=>{if(!el._live)return;any=true;let c=+el.dataset.cur+.25;if(c>=+el.dataset.dur){c=0;el.dataset.state='ready';el._live=false}el.dataset.cur=c;upd(el)});if(!any){clearInterval(tick);tick=null}}
document.addEventListener('pointerdown',e=>{const bar=e.target.closest('.pl-bar');if(!bar)return;const el=bar.closest('.pl');if(el.dataset.state==='error'||el.dataset.state==='loading')return;e.preventDefault();e.stopPropagation();bar.setPointerCapture(e.pointerId);el.classList.add('drag');
  const seek=ev=>{const r=bar.getBoundingClientRect();const p=Math.max(0,Math.min(1,(ev.clientX-r.left)/r.width));el.dataset.cur=p*+el.dataset.dur;if(el.dataset.state==='ready'){el.dataset.state='paused';el._loaded=true}upd(el)};
  seek(e);const mv=ev=>seek(ev);const up=()=>{el.classList.remove('drag');bar.removeEventListener('pointermove',mv);bar.removeEventListener('pointerup',up);bar.removeEventListener('pointercancel',up)};
  bar.addEventListener('pointermove',mv);bar.addEventListener('pointerup',up);bar.addEventListener('pointercancel',up)},true);
})();
