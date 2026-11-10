# EMWAT COM / PE Resource Analyzer results
تاریخ: 2026-11-10
منبع: `EMWAT-COM-Resource-Report.txt`، گزارش اسکن ایستای 70 فایل در `D:\\emwat revers\\EmwatInstaller`.
روش: استخراج رشته‌های ASCII/UTF-16 و فهرست PE Resourceها با pefile؛ هیچ فایل اجرایی اجرا نشده است.

## خلاصه
- گزارش شامل 70 فایل و حدود 2,331 خط است.
- در مجموع 35 hit با برچسب GUID و 24 hit با برچسب ProgID ثبت شده‌اند؛ این تعداد hitهاست، نه تعداد شناسه‌های COM معتبر.
- بسیاری از hitهای ProgID مثبت کاذب‌اند: `JUS_I.B1.002` و `JUS_I.B1.003` نام charset/encoding هستند؛ `excel.sheet`، `word.document` و موارد `*.macroenabled.12` از MIME/media-type database در Delphi RTL آمده‌اند، نه لزوماً ProgIDهای activation.
- GUIDهای مربوط به termination در Agent/Service/Updater، پیام‌های taskbar و Delphi/VCL/Indy نیز در گزارش دیده می‌شوند؛ از روی وجود GUID به‌تنهایی نباید آن‌ها را Office coclass یا COM class دانست.

## یافته‌های معتبر و قابل اتکا

### 1. Word.Application در کد چاپ
رشته literal `Word.Application` در:
- `EmwatMethods.bpl1`، کنار پیام‌های `PrintWordDoc` و انتظار برای تکمیل چاپ MS Word؛
- چند executable از خانواده `GAMPrinterSetup\\zvprtcfg_*`، کنار پیام‌های ارسال فایل برای چاپ و تنظیم delay برای load/quit.

این یافته با شواهد قبلی `TWordApplication` و wrapperهای Word در `EmwatMethods.bpl1` هم‌راستا است. این یک شاهد قوی برای استفاده عملی از Word Automation در مسیر چاپ است؛ اما هنوز ثابت نمی‌کند همه عملیات اسناد به Word وابسته‌اند یا Word تنها backend ممکن است.

### 2. GUIDهای شناسایی‌شده
- `5964933A-7514-48F5-B980-FCB0CBFA97D1`: در Agent کنار نام `_TERMINATE_EM_AGENT` آمده است؛ به‌نظر شناسه پیام/نام‌گذاری داخلی برای پایان Agent است، نه CLSID Office.
- `2EC42BF4-EA08-4476-AB86-466763F80E9A`: در Agent، Service و Updater کنار `_TERMINATE_EM_SERVICE` و task-kill آمده است؛ به‌نظر شناسه داخلی برای پایان Service است.
- `E67A99F0-E7AF-4083-8FD3-B3EBB601C920`: در Service کنار متن Dynamic Config و Emwat Service دیده شده؛ نقش دقیق هنوز نامشخص است.
- `43826D1E-E718-42EE-BC55-A1E261C37BFE`، `D57C7288-D4AD-4768-BE02-9D969532D960`، `84BCCD23-5FDE-4CDB-AEA4-AF64B83D78AB`: در Delphi/VCL و رشته‌های UI ظاهر می‌شوند؛ تا زمان تطبیق با type library/registry به‌عنوان COM classهای EMWAT طبقه‌بندی نشوند.
- `ADB880A6-D8FF-11CF-9377-00AA003B7A11`: در اجزای چاپ/Uninstaller کنار `hhctrl.ocx` و `CLSID\\...\\InprocServer32` دیده می‌شود؛ متعلق به زیرساخت HTML Help است و شاهد embedded browser در EMWAT نیست.
- `e2011457-1546-43c5-a5fe-008deee3d3f0` و `35138b9a-5d96-4fbd-8e2d-a2440225f93a`: GUIDهای supportedOS در manifest برای سازگاری Windows هستند، نه CLSID برنامه.

## Resourceهای PE مهم
- `EmwatMethods.bpl1`: 22 resource؛ شامل RCDATAهای نام‌گذاری‌شده برای فرم‌ها و workflowها، از جمله `TFRMGSCANPREVIEW` (49,193 bytes)، `TFRMIMAGETOOLS` (57,832 bytes)، `TFRMSIMPLEIMAGEEDITOR` (11,451 bytes)، `TFRMWORDPRINTOPTION` (88,487 bytes)، `TFRMFAXRECIPIENTSFORM` (1,774 bytes)، `TFRMSENDLOG` و `TFRMSHOWAUTOSAVEFILES`.
- `EmwatService.exe`: 21 resource؛ شامل `TMAINFORM` (7,507 bytes) و manifest.
- `EmwatAgent.exe`: 80 resource؛ عمدتاً string tables و resourceهای Delphi، به‌علاوه manifest.
- `EmwatUpdate.exe`: 20 resource؛ شامل manifest.
- `GAMPrinterSetup\\zvprtres_x86.dll` و `zvprtres_x64.dll`: resourceهای متعدد DIALOG و STRING؛ این‌ها متعلق به زیرسیستم چاپ هستند و باید جدا از UI اصلی EMWAT تحلیل شوند.

این resource names نشان می‌دهند فرم‌ها و workflowهای گرافیکی بخشی از BPL اصلی در قالب Delphi form resources کامپایل شده‌اند. برای بازسازی Linux، نام و اندازه resourceها به‌تنهایی برای بازسازی layout کافی نیست؛ استخراج و decode محلی DFM/RCDATA و سپس نگاشت کنترل‌ها/رویدادها لازم است.

## نتیجه درباره Browser و Office
- در گزارش هیچ شاهد معتبر و مستقیم از CLSID شناخته‌شده WebBrowser/Internet Explorer، ProgID `Shell.Explorer` یا `InternetExplorer.Application` در فایل‌های اصلی EMWAT ثبت نشده است. این نتیجه فقط به همین اسکن رشته‌ای محدود است و وجود browser host را به‌طور قطعی رد نمی‌کند.
- `Word.Application` و resourceهای `TFRMWORDPRINTOPTION` شواهد Office/Word را تقویت می‌کنند.
- hitهای MIME مانند `word.document` و `excel.sheet` را نباید با COM ProgIDهای Word/Excel اشتباه گرفت.
- GUIDهای داخلی terminate و GUIDهای Delphi/Windows را نباید به CLSID Office نسبت داد.

## ملاحظات کیفیت و حریم خصوصی
- گزارش شامل مسیر محلی `D:\\emwat revers\\EmwatInstaller` و مسیرهای build/PDB فروشنده مانند `C:\\bmpzan\\...` است. این‌ها ظاهراً secret یا داده مشتری نیستند، اما metadata محیط build محسوب می‌شوند؛ اگر مخزن قرار است عمومی شود، بهتر است قبل از انتشار redact شوند.
- اسکریپت گزارش می‌کند PE resourceها را در مسیر محلی استخراج کرده؛ باینری‌های استخراج‌شده در این مخزن commit نشده‌اند.
- بعضی فایل‌های غیر PE یا فایل‌های بسیار کوچک در بخش PE PARSE خطا دارند؛ این برای INI/REG/TXT طبیعی است و به معنی خرابی کل اسکن نیست.

## گام بعدی
1. روی Windows، فقط RCDATAهای `EmwatMethods.bpl1` را محلی بررسی و DFMها را decode کن؛ به‌خصوص `TFRMWORDPRINTOPTION`، `TFRMGSCANPREVIEW` و `TFRMIMAGETOOLS`.
2. خروجی متنی decode شده و بدون داده عملیاتی/مشتری را ارائه کن؛ resourceهای خام را در GitHub آپلود نکن.
3. برای تعیین COM activation، فقط registry keys مرتبط با `Word.Application` و `Excel.Application` را از سیستم مرجع بررسی کن؛ export کل Registry لازم نیست.
4. سپس workflowهای Word/Excel، اسکن/تصویر و چاپ را به specification قابل تست تبدیل کن.
