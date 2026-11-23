# EMWAT-Linux

بازسازی بومی EMWAT برای Linux با هدف حفظ گردش‌کار واقعی الماس گام از طریق LibreOffice Writer. هدف محصول فقط Linux است؛ Windows صرفاً مرجع تحلیل و سازگاری است.

> نسخه نهایی قرار نیست با Wine اجرا شود. فایل‌های Windows فقط مرجع تحلیل و سازگاری هستند.

## تصمیم‌های قطعی محصول و معماری

- فقط Linux؛ توسعه نسخه یا نصب‌کننده Windows در دامنه پروژه نیست.
- رابط کنترلی سبک: GTK 4 با Python/PyGObject؛ بدون Qt/PySide و بدون هزینه مجوز.
- ویرایش سند: LibreOffice Writer از طریق UNO؛ GTK ویرایشگر سند نیست.
- نقش EMWAT: پل محلی بین سامانه مکاتبات الماس و Writer؛ دریافت سند، اجرای گردش‌کار ویرایش و بازگرداندن نتیجه به الماس.
- هسته پروتکل، هماهنگ‌کننده سند، UNO، Recovery و Scanner مستقل از GTK باقی می‌مانند؛ GUI فقط لایه نمایش است.

مرجع قطعی و جزئیات تصمیم‌ها: [تصمیم‌های محصول Linux و معماری](docs/LINUX-PRODUCT-DECISIONS.md).

## کاربرد واقعی و هدف پروژه

EMWAT واسط محلی بین اتوماسیون تحت وب الماس گام و برنامه‌های دسکتاپ کاربر است. گردش‌کار اصلی شناخته‌شده، دریافت اطلاعات و قالب نامه از الماس گام، بازکردن Word برای تکمیل/ویرایش نامه و بازگرداندن فایل پس از پایان کار به همان سامانه است. بعضی نامه‌ها نیز کاملاً تصویری‌اند؛ بنابراین قابلیت‌های اسکن و پردازش تصویر در دامنه پروژه باقی می‌مانند.

جزئیات تأییدشده، شواهد فنی، موارد نامشخص و نقشه راه بازتنظیم‌شده در [تحلیل گردش‌کار واقعی EMWAT](docs/PRODUCT-WORKFLOW-ANALYSIS.md) ثبت شده‌اند.

## وضعیت فعلی

پروژه از مرحله تحلیل اولیه عبور کرده و اکنون هسته‌های Python، پل HTTP محلی، parser/dispatcher، مسیر EditWordDocument، اتصال LibreOffice UNO، بازیابی دوره‌ای، ذخیره‌سازی اختیاری رمزگذاری‌شده و backend اولیه اسکن SANE را دارد. یک نمای اولیه GTK4 برای Recovery نیز به‌صورت لایه اختیاری اضافه شده است؛ اما هنوز رابط کامل برنامه، اجرای واقعی در مرورگر الماس گام، mapping کامل فیلدهای Word، قراردادهای Cancel/Discard و بسته‌بندی اجرایی نهایی باقی مانده‌اند.

گزارش کامل وضعیت، شواهد، موارد نامشخص و گام‌های بعدی در این فایل نگهداری می‌شود:

- [گزارش وضعیت و نقطه ادامه پروژه](docs/PROJECT-STATUS.md)
- [قرارداد چرخه ارتباطی Almas و Writer و مرزهای Save/Close/Cancel](docs/ALMAS-WRITER-LIFECYCLE-CONTRACT.md)
- [شواهد و مرز سازگاری آرشیو Windows .easz](docs/EASZ-ARCHIVE-FORMAT.md)
- [قرارداد Recovery و رمزنگاری اختیاری AES-GCM](docs/RECOVERY-RETENTION.md)
- [قرارداد کاتالوگ و بازیابی Recovery](docs/RECOVERY-CATALOG.md)
- [طراحی UX انتخاب و بازیابی نسخه‌ها](docs/RECOVERY-PICKER-UX.md)
- [نقشه پیاده‌سازی بومی لینوکس و مسیرهای موازی](docs/LINUX-NATIVE-IMPLEMENTATION-PLAN.md)
- [راهنمای نصب Ubuntu و مرزهای پذیرش یکپارچه‌سازی](docs/UBUNTU-INSTALLATION-AND-INTEGRATION.md)
- [اعتبارسنجی runtime نسخه Windows با Winux/Wine](docs/WINUX-RUNTIME-VALIDATION.md)
- [تحلیل گردش‌کار واقعی EMWAT در الماس گام](docs/PRODUCT-WORKFLOW-ANALYSIS.md)
- [تحلیل connector و ساختار XML گردش‌کار Word](docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md)
- [تحلیل ایستای چرخه Word و اختلاف VMT/TD32](docs/WORD-LIFECYCLE-STATIC-TRACE.md)
- [تحلیل سرویس HTTP محلی و bridge](docs/HTTP-LOCAL-API-ANALYSIS.md)
- [تحلیل Import Table و وابستگی‌های Windows](docs/IMPORT-TABLE-ANALYSIS.md)
- [تحلیل Office Automation و COM](docs/OFFICE-COM-ANALYSIS.md)
- [تحلیل COM و PE Resourceهای استخراج‌شده](docs/RESOURCE-ANALYSIS.md)
- [تحلیل ساختار فرم تنظیمات چاپ Word](docs/WORD-PRINT-OPTION-DFM.md)
- [تحلیل فرم پیش‌نمایش اسکن و ابزارهای تصویر](docs/SCAN-PREVIEW-DFM.md)
- [تحلیل فرم اصلی مدیریت و ویرایش تصاویر](docs/IMAGE-TOOLS-DFM.md)
- [تحلیل ویرایشگر ساده تصویر و مقایسه سه فرم](docs/SIMPLE-IMAGE-EDITOR-DFM.md)
- [نقشه وابستگی‌های ImageGear و ImageEn](docs/Imaging-Dependency-Map.md)
- [گراف فراخوانی‌های تصویر و اسکن](docs/IMAGE-CALL-GRAPH.md)
- [تحلیل دقیق APIهای ImageGear](docs/GEAR-API-CALLS.md)
- [تحلیل قرارداد انتخاب اسکنر و رابط‌های callback](docs/SCANNER-INTERFACE-ANALYSIS.md)
- ابزار [استخراج GUID/ProgID و Resourceها](tools/EMWAT-COM-Resource-Analyzer.py)

## گزارش‌ها و فایل‌های مرجع موجود

- `EMWAT_Extracted.zip` — آرشیو فایل‌های استخراج‌شده برای تحلیل
- `EmwatService.exe-strings.txt`
- `EmwatAgent.exe-strings.txt`
- `EmwatMethods.bpl1-strings.txt`
- `EMWAT-Analysis-Results.txt` — خروجی فیلترشده و تجمیع‌شده
- `EMWAT-Import-Report.txt` — خروجی Import Table سه فایل اصلی

گزارش‌های رشته‌ای فقط سرنخ هستند؛ وجود نام یک کلاس یا کتابخانه به‌تنهایی فعال‌بودن یک قابلیت را ثابت نمی‌کند.

## اصول توسعه

1. هدف، نسخه مستقل و بومی Linux است؛ Wine بخشی از راهکار نهایی نیست.
2. پیش از پیاده‌سازی، API، دیتابیس، فایل‌ها، فرمول‌ها و گردش‌کارهای نسخه اصلی مستند شوند.
3. Python زبان اصلی پل و برنامه است؛ رابط گرافیکی سبک با GTK 4 و PyGObject ساخته می‌شود.
4. LibreOffice Writer از طریق UNO موتور ویرایش سند در Linux است؛ سازگاری باید با تست واقعی تأیید شود.
5. رابط GTK فقط کنترل/تنظیمات/Recovery/وضعیت را ارائه می‌کند و نباید منطق پروتکل یا سند را در خود جای دهد.
6. هیچ موتور دیتابیسی تا زمان شناسایی شواهد واقعی به‌عنوان انتخاب نهایی تثبیت نشود.
7. فایل‌های اجرایی، داده‌های مشتریان، کلیدها و اطلاعات محرمانه نباید در مخزن عمومی قرار بگیرند. گزارش‌های خام نیز پیش از commit باید از نظر اطلاعات حساس بازبینی شوند.

## نقطه ادامه پروژه

با توجه به کاربرد واقعی که از کاربر تأیید شده، اولویت بعدی دیگر صرفاً توسعه موتور اسکن نیست. ابتدا باید قرارداد ارتباطی bridge مرورگر و سرویس Windows، dispatch متدها و انتقال فایل را از روی BPL و یک سناریوی runtime استخراج کنیم. سپس یک نمونه انتها‌به‌انتها برای نامه متنی با LibreOffice بسازیم. موتور تصویر و اسکن حفظ می‌شود و پس از روشن‌شدن گردش‌کار نامه‌های تصویری تکمیل خواهد شد.

برای ترتیب دقیق کارها و مواردی که هنوز نیازمند آزمایش هستند، [تحلیل گردش‌کار واقعی EMWAT](docs/PRODUCT-WORKFLOW-ANALYSIS.md) و [گزارش وضعیت پروژه](docs/PROJECT-STATUS.md) را ببینید.

## Session continuity

For the current project decisions, implementation boundaries, and next-session checklist, see [docs/SESSION-HANDOFF.md](docs/SESSION-HANDOFF.md).

## وضعیت پیاده‌سازی هسته Linux

در شاخه توسعه فعلی، اجزای زیر پیاده‌سازی شده‌اند:

- **HTTP bridge:** listener محدود به IPv4 loopback، heartbeat و init route، کنترل Origin/Host و framing، سقف درخواست/پاسخ و timeout.
- **Protocol:** parser محافظه‌کارانه XML و dispatcher با allowlist؛ کلاس متد هرگز به‌صورت پویا import نمی‌شود.
- **EditWordDocument:** decode کردن Base64 تأییدشده‌ی `wordConfig` و `wordBody`، اعتبارسنجی حدود اندازه و نگه‌داشتن `signData` به‌صورت opaque text تا زمان اثبات encoding کامل آن.
- **Writer:** اجرای close-driven با LibreOffice UNO، snapshot نهایی DOC و بازگرداندن پاسخ موفق با envelope مشاهده‌شده‌ی `response-word`.
- **Recovery:** snapshot دوره‌ای محلی، catalog و restore صریح؛ retention و AES-256-GCM رمزگذاری‌شده opt-in هستند و کلید رمزگذاری از Secret Service گرفته می‌شود.
- **Scanner:** backend مبتنی بر SANE با اعتبارسنجی گزینه‌ها و محدودیت اندازه‌ی frame؛ سخت‌افزار واقعی، ADF و duplex هنوز تأیید نشده‌اند.

تست‌ها شامل Python unit/transport، build و ASan/UBSan برای native core و roundtrip واقعی LibreOffice UNO هستند. آخرین ترکیب کد تأییدشده در 2026-11-18:

- Python bridge: [run 44305529480](https://github.com/meicamghe/EMWAT-Linux/actions/runs/44304965568) — 198 تست، 196 موفق و 2 تست اختیاری UNO skip شدند.
- Native build + ASan/UBSan: [run 44305529408](https://github.com/meicamghe/EMWAT-Linux/actions/runs/44304965055) — هر دو job موفق.
- LibreOffice UNO: [run 44305529564](https://github.com/meicamghe/EMWAT-Linux/actions/runs/44304965075) — runtime و roundtrip واقعی Writer موفق.

### مواردی که هنوز تکمیل نشده‌اند

- اجرای end-to-end از صفحه واقعی الماس گام و بررسی دقیق Origin، پیام‌ها و پاسخ‌ها.
- mapping معنایی همه فیلدهای Word به Writer و آزمون با fixture بی‌خطر و واقعی.
- encoding و association کامل `signData`، تصویر/امضا و فیلدهای سفارشی.
- قرارداد wire response برای Cancel و Discard؛ این سیاست هنوز تزریق‌شدنی است و حدس زده نشده.
- GUI واقعی برای انتخاب/بازیابی snapshot، تنظیمات و مدیریت اسکن.
- entrypoint اجرایی، بسته‌بندی نصب/حذف و integration با session دسکتاپ.
- آزمون سخت‌افزار اسکنر، ADF/duplex و سازگاری Windows `.easz`.

**وضعیت انتشار:** تغییرات روی PR شماره ۲ در حالت Draft نگه داشته شده‌اند و هنوز به main ادغام نشده‌اند. این مخزن یک هسته‌ی در حال توسعه است، نه محصول آماده‌ی نصب و استفاده‌ی روزمره.


## آخرین پذیرش دستی Writer — 2026-11-23

رفتار قابل مشاهده‌ی LibreOffice Writer برای سه حالت Save، Don't Save و
Cancel-سپس-بستن دوباره، روی Ubuntu آزمایش شده و موفق بوده است. نسخه برگشتی
از آخرین وضعیت ذخیره‌شده‌ی تأییدشده ساخته می‌شود؛ snapshot بازیابی دوره‌ای
جایگزین پاسخ نهایی نیست. جزئیات و شواهد markerها در
[گزارش تست تعاملی Writer](docs/WRITER-CLOSE-ACCEPTANCE-TEST.md) آمده است.

این نتیجه فقط رفتار محلی Writer/UNO را می‌پوشاند. اتصال زنده به صفحه الماس گام،
قرارداد دقیق پاسخ‌های Windows برای Cancel/Discard، mapping کامل فیلدهای Word،
رابط کامل دسکتاپ و بسته نصب نهایی هنوز تکمیل نشده‌اند. پروژه هنوز آماده انتشار
یا استفاده عملیاتی نیست.
