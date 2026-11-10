# EMWAT Import Table — یافته‌های تحلیل ایستا
آخرین به‌روزرسانی: 2026-11-10
منبع: `EMWAT-Import-Report.txt` در مخزن
وضعیت: تحلیل import table فایل‌های PE؛ بدون اجرای برنامه. Import به معنی وابستگی/قابلیت قابل فراخوانی است و به‌تنهایی ثابت نمی‌کند مسیر در هر workflow اجرا می‌شود.

## 1. جمع‌بندی اجرایی

| حوزه | نتیجه | اطمینان |
|---|---|---|
| معماری و زبان | فایل‌ها PE32/x86 و وابسته به بسته‌های Delphi 10 Seattle (230) هستند. | بالا |
| HTTP | شواهد قبلی Indy HTTP server در Service و importهای Indy در Methods با هم سازگارند. | بالا |
| دیتابیس | در importهای گزارش‌شده، DLL/API صریحی برای SQLite، ODBC، SQL Server، MySQL یا PostgreSQL دیده نشد. موتور DB همچنان نامشخص است. | متوسط؛ نبودن import مستقیم، استفاده پویا/از طریق COM یا ماژول دیگر را رد نمی‌کند |
| Office/COM | در Agent، `CoCreateInstance`, `GetActiveObject`, `ProgIDFromCLSID`, `Variant*` و SafeArrayها دیده می‌شوند؛ این شواهد از استفاده COM/OLE و احتمال اتوماسیون برنامه‌های Office پشتیبانی می‌کند. | بالا برای COM؛ متوسط برای Office تا CLSID/ProgID مشخص شود |
| Browser | import مستقیم شناخته‌شده‌ای از `mshtml.dll`, `urlmon.dll`, `wininet.dll`, `winhttp.dll` در بخش‌های بررسی‌شده دیده نشد. این موضوع IE/WebView را رد نمی‌کند؛ ممکن است از COM/ActiveX یا بارگذاری پویا استفاده شود. | متوسط |
| اسکن/تصویر | Methods به `GEAR32PD.DLL` و APIهای اسکن/تصویر، و به پکیج `PKIECtrl23.bpl` با نمادهای WIA/TWAIN و ImageEn متصل است. | بالا برای وجود dependency |
| چاپ | Service و Methods به `winspool.drv` متصل‌اند و APIهای enumeration/open/configuration چاپگر را وارد می‌کنند. | بالا |
| گرافیک | Methods به `gdiplus.dll` با مجموعه بزرگ GDI+ و به GDI متصل است. | بالا |
| Windows integration | Registry، process/thread، event log، shell folders، WTS session notifications و network workstation info در imports دیده می‌شوند. | بالا |

## 2. EmwatService.exe

### DLLها و APIهای مهم
- `kernel32.dll`: `LoadLibraryA`, `GetProcAddress`, `CreateFileW`, `CreateMutexW`, `FindFirstFileW`, `GetTempPathW`, `TerminateProcess` و توابع پایه thread/synchronization.
- `user32.dll`: `RegisterWindowMessageW`, `PostMessageW`, `FindWindowW`, `GetWindowTextW`؛ یعنی تعامل با پنجره‌ها و پیام‌های ویندوز.
- `advapi32.dll`: `RegisterEventSourceW`, `ReportEventW`؛ پشتیبانی از Windows Event Log.
- `shell32.dll`: `ShellExecuteW`, مسیرهای known/special folders.
- `winspool.drv`: `OpenPrinterW`, `EnumPrintersW`, `GetDefaultPrinterW`, `DocumentPropertiesW`, `ClosePrinter`.
- `IndyProtocols230.bpl`: نمادهای HTTP server از جمله `TIdHTTPResponseInfo.WriteContent`؛ همسو با شواهد رشته‌ای قبلی درباره Indy HTTP.
- `xmlrtl230.bpl`: XML document/node support.
- اجزای VCL/RTL Delphi و Windows graphics/UI.

### برداشت
Service فقط یک پردازش ساده شبکه‌ای نیست؛ به Windows UI messaging، Event Log، Registry/RTL، چاپگرها و XML نیز وابستگی دارد. در importهای مستقیم Service، driver شناخته‌شده SQL/ODBC مشخص نشده است.

## 3. EmwatAgent.exe

### DLLها و APIهای مهم
- `advapi32.dll`: `RegOpenKeyExW`, `RegQueryValueExW`, `OpenProcessToken`, `LookupPrivilegeValueW`, `LookupAccountSidW`, `GetTokenInformation`, `AdjustTokenPrivileges`, `GetUserNameW`.
- `ole32.dll`: `CoInitialize`, `CoInitializeEx`, `CoCreateInstance`, `GetActiveObject`, `ProgIDFromCLSID`, `OleInitialize`.
- `oleaut32.dll`: BSTR، VARIANT و SAFEARRAY APIs مانند `SysAllocStringLen`, `VariantChangeType`, `VariantCopy`, `SafeArrayCreate`.
- `netapi32.dll`: `NetWkstaGetInfo` برای اطلاعات workstation.
- `wtsapi32.dll`: `WTSRegisterSessionNotification`, `WTSUnRegisterSessionNotification`.
- `winspool.drv`: APIهای بازکردن و فهرست‌کردن چاپگرها.
- `shell32.dll`: اجرای shell و دسترسی به پوشه‌های ویژه.
- `kernel32.dll`: process/thread, file, memory, events, profile INI و توابع سیستم.
- `user32.dll`, `gdi32.dll`, `comctl32.dll`, `uxtheme.dll`, `DWMAPI.DLL`, `windowscodecs.dll`: UI، گرافیک، تم و تصویر.

### برداشت
وجود COM/OLE و Variant/SafeArray در Agent قطعی است. این می‌تواند برای اتصال به برنامه‌های Automation مانند Word/Excel استفاده شود، اما برای اثبات هدف دقیق باید CLSID/ProgIDها و call siteها یا رفتار runtime بررسی شوند. WTS notifications نشان می‌دهد Agent از تغییرات session ویندوز آگاه می‌شود؛ این با نقش Agent/sentinel سازگار است، ولی سیاست دقیق restart هنوز معلوم نیست.

## 4. EmwatMethods.bpl1

### DLLها و packageهای مهم
- `IndySystem230.bpl`, `IndyCore230.bpl`, `IndyProtocols230.bpl`: کتابخانه Indy. `wsock32.dll` و `gethostname` نیز در importها دیده می‌شوند. این با وجود networking code سازگار است، اما endpointهای کامل از این گزارش به دست نمی‌آیند.
- `GEAR32PD.DLL`: APIهای `IG_scan_pages`, `IG_scan_source_select`, `IG_load_file`, `IG_save_file`, `IG_save_JPEG_quality_set`, `IG_image_resolution_get/set`, `IG_IP_crop`, `IG_IP_rotate_multiple_90` و سایر توابع پردازش تصویر.
- `PKIECtrl23.bpl`: نمادهای `Iewia`, `Ietwain`, `TImageEnMIO.Acquire`, `TImageEnMIO.LoadFromFileAuto`, `TImageEnMIO.SaveToFile`, `TImageEnMIO.SaveToFileTIFF`, `TImageEnView`, `TImageEnProc.Rotate/CropSel/SkewDetection`. این‌ها شواهد قوی dependency به ImageEn و مسیرهای WIA/TWAIN هستند.
- `winspool.drv`: `OpenPrinterA/W`, `EnumPrintersA/W`, `GetPrinterA`, `EnumJobsW`, `ClosePrinter`.
- `gdiplus.dll`: مجموعه گسترده GDI+ برای متن، فونت، تصویر، bitmap، encoder/decoder، metafile و رسم.
- `xmlrtl230.bpl`: XML DOM.
- `shell32.dll`: `ShellExecuteW`, special folders.
- `ole32.dll` و `oleaut32.dll`: OLE initialization و BSTR/Automation support.
- Delphi VCL/RTL و TeeChart (`Tee9230.bpl`) symbols.

### برداشت
Methods package یک لایه مهم desktop/document-imaging integration دارد: scan/acquire، پردازش تصویر، TIFF/JPEG، چاپ، XML، نمودار و COM. وجود WIA/TWAIN symbols لااقل dependency در پکیج را نشان می‌دهد، نه تضمین اینکه تمام دستگاه‌ها/فرمت‌ها در محصول نهایی فعال‌اند.

## 5. پاسخ فعلی به پرسش‌های اصلی

### آیا دیتابیس شناسایی شد؟
خیر. در این import report هیچ اتصال مستقیم آشکاری به SQLite، ODBC، SQL Server، MySQL یا PostgreSQL دیده نشده است. گام بعدی باید بررسی فایل‌های کنار برنامه، نام DLLهای همراه، strings هدفمند در تمام فایل‌ها و تنظیمات غیرحساس باشد. همچنین ممکن است دیتابیس از طریق COM، BPL بارگذاری‌شده، DLL پویا یا سرویس بیرونی قابل دسترسی باشد.

### آیا موتور مرورگر شناسایی شد؟
خیر. import مستقیم `mshtml`, `urlmon`, `wininet`, `winhttp` در گزارش فعلی مشخص نشده است. با این حال وجود bridge جاوااسکریپتی `postMessage` از تحلیل رشته‌ها و importهای COM/ActiveX، احتمال استفاده از یک host وب/COM را باز می‌گذارد. برای تشخیص باید resourceها، CLSID/ProgID، نام کلاس‌های window و registry setup بررسی شوند.

### آیا Office Automation تأیید شد؟
COM/OLE تأیید شده، Office هنوز قطعی نیست. قدم بعدی استخراج CLSID/ProgIDها و strings مربوط به `Excel.Application`, `Word.Application`, `Outlook.Application`, `Workbook`, `Document`, `Workbooks`, `Documents` از Agent و Methods و تطبیق آن با typeinfo است.

## 6. ریسک‌ها و ملاحظات بازسازی Linux

1. چاپ و اسکن باید به‌صورت subsystem مستقل طراحی شوند؛ CUPS و SANE گزینه‌های بررسی برای Linux هستند، اما رفتار، قالب و قابلیت‌های اختصاصی دستگاه باید تست شوند.
2. GDI+ drawing/bitmap و ImageEn processing نیاز به معادل‌سازی و regression test دارند؛ Pillow/OpenCV/Cairo/Qt قابل ارزیابی‌اند، نه انتخاب قطعی.
3. COM Automation ویندوزی را نمی‌توان مستقیم به Linux منتقل کرد. باید قراردادهای عملی Word/Excel و فرمت‌های ورودی/خروجی استخراج و سپس LibreOffice UNO یا تبدیل مبتنی بر فایل بررسی شود.
4. Indy HTTP را می‌توان با یک HTTP server پایتونی جایگزین کرد، اما فقط پس از استخراج قرارداد payload و خطاها.
5. imports نبودن DB driver دلیل نبود دیتابیس نیست؛ فقط می‌گوید در این فایل‌ها import مستقیم شناخته‌شده‌ای دیده نشده است.

## 7. گام‌های بعدی

1. استخراج CLSID/ProgID و رشته‌های Office/COM از Agent و Methods.
2. جست‌وجوی هدفمند نام DLLها و فرمت‌های DB در تمام فایل‌های ZIP استخراج‌شده؛ بررسی config/INI/REG و فایل‌های داده با احتیاط.
3. تحلیل resourceهای Service و Agent برای شناسایی dialogها، iconها، manifest و احتمال embedded browser/ActiveX.
4. تحلیل پوشه GAMPrinterSetup به‌عنوان پروژه فرعی: تعیین نام/نسخه driver، سرویس‌های چاپ و معماری x86/x64.
5. تهیه ماتریس قابلیت‌ها و اولویت‌بندی بر اساس نیاز واقعی کاربر و evidence.
6. پس از آن، طراحی prototype Linux برای local API، document bridge و scan/print adapters.

## 8. محدودیت گزارش
این سند از import table استخراج‌شده توسط pefile و شواهد strings قبلی ساخته شده است. این تحلیل dynamic API resolution را کامل پوشش نمی‌دهد؛ `LoadLibrary`/`GetProcAddress` در Service و Agent دیده شده‌اند، بنابراین برخی DLLها ممکن است در زمان اجرا بارگذاری شوند و در import table عادی دیده نشوند. همچنین بخش بزرگی از importها مربوط به Delphi RTL/VCL و packageهای همراه است و نباید به‌عنوان قابلیت مستقل محصول تفسیر شود.
