# أدوات المعارض (مصدر بيانات واحد)

مصدر الحقيقة: `data/exhibitions.json` — كل معرض فيه: `page`, `name`, `status` (confirmed/tbd), وللمؤكد: `start`, `end`, `date_text`, `venue`, `blurb`, `cal_title`, `gcal_title`, `gcal_venue`, `ics_uid`, `ics_summary`, `ics_location`.

السكريبت `tools/sync_exhibitions.py` بيولّد ويتحقق من: ملف الـ ICS، الكاليندر (الشهور + الكروت + الفهرس + ItemList + العدّادات)، تواريخ وعدّادات الدليل، كروت الرئيسية (أقرب 5 معارض)، `llms.txt`، و`search-index.js`، ويقارن صفحة كل معرض (العدّاد + السكيما) بالـ JSON.

الاستخدام من جذر الريبو:
- `python3 tools/sync_exhibitions.py --check` — يعرض أي ملف خارج التزامن أو أي صفحة معرض ما بتطابقش الـ JSON.
- `python3 tools/sync_exhibitions.py --apply` — يكتب الملفات المتغيرة.

إضافة معرض جديد: (1) اعمل صفحته (انسخ صفحة معرض مشابه)، (2) ضيفه في `data/exhibitions.json`، (3) ضيفه يدويًا في كروت الدليل وصفحة قسمه (hub) — دول لسه مش متولّدين، (4) شغّل `--apply` ثم `--check`.
معرض خلصت دورته: غيّر status إلى tbd وامسح الحقول المؤكدة، وخلي صفحته بحالة EventCompleted وبدون عدّاد.
