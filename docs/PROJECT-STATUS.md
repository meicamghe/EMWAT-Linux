# وضعیت پروژه EMWAT-Linux
آخرین به‌روزرسانی: 2026-11-11

## هدف قطعی
بازسازی بومی EMWAT برای Linux با حفظ رفتار و گردش‌کارهای واقعی نسخه Windows. اجرای نسخه Windows با Wine راهکار محصول نهایی نیست. LibreOffice به‌عنوان جایگزین/پل تعامل با اسناد و صفحه‌گسترده‌ها در نظر گرفته شده، اما روش اتصال تا روشن‌شدن رفتار واقعی برنامه تعیین نمی‌شود.

## وضعیت مخزن و شواهد موجود
- مخزن: https://github.com/meicamghe/EMWAT-Linux
- شاخه اصلی: `main`
- فایل مرجع استخراج‌شده: `EMWAT_Extracted.zip`
- گزارش‌های رشته‌ای موجود:
  - `EmwatService.exe-strings.txt`
  - `EmwatAgent.exe-strings.txt`
  - `EmwatMethods.bpl1-strings.txt`
  - `EMWAT-Analysis-Results.txt` (خروجی فیلترشده و تجمیع‌شده)
- گزارش‌ها شواهد استخراج رشته‌ها هستند، نه سورس‌کد. رشته‌های تصادفی/خراب و نام کلاس‌ها به‌تنهایی اثبات نمی‌کنند یک قابلیت در نسخه نصب‌شده فعال یا قابل استفاده است.

## شناسایی فنی تأییدشده
- محصول در فراداده با نام Empowered Web Application Technology (Emwat) / Emwat Service و شرکت GamElectronics معرفی شده است.
- فایل‌های اصلی بررسی‌شده PE32 و x86 هستند.
- فایل‌های BPL با پسوند/شماره بسته `230` با Delphi 10 Seattle سازگارند.
- سرویس از اجزای Indy مانند `TIdHTTPServer` و `TIdCustomHTTPServer` استفاده می‌کند.
- سرویس نام/رشته‌های مربوط به `EmwatMethods.bpl` را دارد و بارگذاری این BPL در رشته‌ها دیده می‌شود.
- پورت محلی پیش‌فرضی که در رشته‌ها صریحاً دیده شده `1984` است؛ پیام خطا می‌گوید اگر پورت اشغال باشد binding شکست می‌خورد.
- Agent رشته heartbeat به نشانی `http://127.0.0.1:1984/?heartbeat` دارد و نام/رشته‌های sentinel و reliability نیز در آن دیده می‌شود.
- در Service یک bridge جاوااسکریپت دیده شده که پیام `postMessage` را با HTTP POST به `127.0.0.1:<myport>?invoke=<random>` می‌فرستد و پاسخ `responseText` را به پنجره والد برمی‌گرداند. این شواهد معماری ارتباط UI وب‌مانند با سرویس محلی را تقویت می‌کند؛ مرورگر/موتور دقیق هنوز قطعی نشده است.
- رشته‌های XML برای متدهای `ShowEmwatSetting`، `ShowLastEditedDocs` و `ShowSendLog` وجود دارند.
- رشته‌های کلید رجیستری `Software\\Emwat\\Dynamic Config` دیده شده‌اند.
- در BPL اصلی نام‌ها و type informationهای فراوانی برای اتوماسیون Word/Excel، XML، تصویر/اسکن/WIA، چاپ، ایمیل/SMTP، فکس و نمودار وجود دارد. این‌ها سرنخ قابلیت‌ها هستند و باید با رفتار اجرایی/نمونه گردش‌کار تأیید شوند.
- رشته‌های `.mdb` و ODBC که در برخی فایل‌ها دیده شده‌اند، به‌تنهایی اثبات نمی‌کنند دیتابیس برنامه Microsoft Access یا ODBC است. موتور پایگاه داده هنوز شناسایی نشده است.

## اجزای شناخته‌شده
- `EmwatService.exe`: سرویس اصلی؛ میزبان HTTP محلی بر اساس رشته‌های Indy.
- `EmwatAgent.exe`: Agent با heartbeat به سرویس محلی و رشته‌های sentinel/reliability.
- `EmwatMethods.bpl1`: کتابخانه منطق/متدها و wrapperهای اتوماسیون؛ جزئیات داخلی هنوز نیازمند تحلیل بیشتر است.
- `EmwatUpdate.exe`: ابزار به‌روزرسانی؛ رفتار و endpointهای آن هنوز روشن نیست.
- `GAMPrinterSetup.exe` و پوشه `GAMPrinterSetup`: ابزارها و DLL/EXEهای متعدد مرتبط با زیرساخت چاپ؛ جزئیات پروتکل/وابستگی باید جداگانه بررسی شود.
- `klc.exe`: فراداده آن «Farsi Keyboard in Office Automation Forms» را نشان می‌دهد؛ KLC، نسخه 1.0.3.9411.

## مواردی که هنوز نباید قطعی فرض شوند
1. نوع، schema و محل پایگاه داده.
2. API کامل سرویس، مسیرها، verbها، قالب درخواست/پاسخ و احراز هویت.
3. اینکه UI دقیقاً از Internet Explorer، WebBrowser control یا موتور دیگری استفاده می‌کند.
4. فهرست قابلیت‌های واقعاً فعال و گردش‌کارهای اصلی کاربر.
5. قالب فایل‌های داده، الگوها، فرم‌ها و گزارش‌ها.
6. رفتار به‌روزرسانی، ارتباط شبکه‌ای خارجی و وابستگی‌های امنیتی.
7. امکان جایگزینی کامل Office Automation با LibreOffice و نقاط تفاوت.

## تصمیم‌های معماری نسخه Linux
- هدف نسخه بومی Linux است؛ عدم اتکا به Wine.
- پیاده‌سازی اولیه با Python قابل بررسی است، اما انتخاب framework نهایی پس از تکمیل تحلیل رفتار و مرزهای سرویس انجام شود.
- ارتباط داخلی می‌تواند از یک API محلی امن استفاده کند؛ طراحی دقیق باید پس از استخراج قرارداد واقعی درخواست/پاسخ انجام شود.
- برای فایل‌ها و اسناد، ODF/OOXML و LibreOffice بررسی شوند؛ تبدیل قالب نباید بدون تست سازگاری انجام شود.
- تا روشن‌شدن دیتابیس، هیچ موتور خاصی را به‌عنوان انتخاب نهایی تثبیت نکنید.
- داده‌های مشتریان، کلیدها، اطلاعات ورود و داده‌های شخصی نباید در مخزن یا گزارش‌های عمومی قرار بگیرند. پیش از commit گزارش‌های خام، آن‌ها را از نظر اطلاعات حساس بازبینی کنید.

## تحلیل تکمیلی انجام‌شده در 2026-11-10
- سند مستقل [تحلیل HTTP محلی و bridge](HTTP-LOCAL-API-ANALYSIS.md) اضافه شد.
- شواهد heartbeat و invoke در قالب جدول مستند شدند و مدل ارتباطی موقت ترسیم شد.
- موارد نامعلوم API و ملاحظات امنیتی نسخه Linux تفکیک شدند.
- Import Table سه فایل Service، Agent و Methods استخراج و در [گزارش تحلیل Importها](IMPORT-TABLE-ANALYSIS.md) مستند شد.
- COM/OLE در Agent، dependencyهای Indy در Service/Methods، چاپگرهای Windows، ImageEn/WIA/TWAIN، GEAR32PD و GDI+ شناسایی شدند.
- در importهای مستقیم گزارش‌شده، driver صریح دیتابیس و import مستقیم شناخته‌شده مرورگر پیدا نشد؛ این موارد همچنان باز هستند، چون بارگذاری پویا ممکن است.
- تحلیل تکمیلی typeinfo نشان داد wrapperهای صریح Word و Excel در Methods وجود دارند؛ COM/OLE و Office Automation اکنون با اطمینان بسیار بالا تأیید شده‌اند. جزئیات در [تحلیل Office/COM](OFFICE-COM-ANALYSIS.md) ثبت شد.
- رشته‌های CLSID/ProgID literal هنوز یافت نشده‌اند؛ نبود literal، activation پویا یا GUIDهای binary/typeinfo را رد نمی‌کند.
- نماد `TWordApplication.Get_Browser` به object model خود Word تعلق دارد و نباید به‌عنوان اثبات embedded browser استفاده شود.
- ابزار مرحله بعد [EMWAT-COM-Resource-Analyzer.py](../tools/EMWAT-COM-Resource-Analyzer.py) به مخزن اضافه شد. این ابزار GUID/ProgIDهای محتمل را در فایل‌ها و resourceهای PE جست‌وجو می‌کند و resourceها را محلی استخراج می‌کند.
- ابزار روی 70 فایل در `D:\\emwat revers\\EmwatInstaller` اجرا شد و گزارش `EMWAT-COM-Resource-Report.txt` با موفقیت در مخزن قرار گرفت؛ فایل‌های resource خام آپلود نشده‌اند.
- گزارش Resource Analyzer در [تحلیل COM و PE Resourceها](RESOURCE-ANALYSIS.md) ثبت شد: literal `Word.Application` در مسیر چاپ تأیید شد؛ hitهای MIME/charset از ProgIDهای واقعی تفکیک شدند؛ GUIDهای terminate سرویس/Agent از CLSIDهای Office جدا شدند.
- فرم `TfrmWordPrintOption` از `EmwatMethods.bpl1` از مسیر `analysis-input/RCDATA_TFRMWORDPRINTOPTION_19.bin` دریافت و decode شد: 34 component، عنوان «تنظیمات چاپ»، انتخاب چاپگر، گیرندگان/CC، محدوده صفحات و شمارنده‌های نسخه استخراج شدند. جزئیات در [WORD-PRINT-OPTION-DFM.md](WORD-PRINT-OPTION-DFM.md) است. سه فرم Scan Preview، Image Tools و Simple Image Editor هنوز decode نشده‌اند.

## گام‌های بعدی تحلیل
1. بررسی strings و typeinfo انجام شد؛ Word/Excel Automation مستند شد.
2. تحلیل گزارش COM/Resource انجام شد؛ فرم Word Print به‌صورت کامل از Binary DFM decode شد. گام بعد decode سه فرم اسکن/تصویر و بررسی هدفمند Registry فقط برای Word/Excel است.
3. بررسی فایل‌های config/INI/REG و محتوای پوشه چاپ؛ ثبت فقط مقادیر غیرحساس.
4. شناسایی دقیق قرارداد heartbeat و invoke: پارامترها، payload، پاسخ‌ها و مسیرهای دیگر HTTP.
5. شناسایی دیتابیس از روی فایل‌های واقعی، importها، driverها و تنظیمات؛ نه از روی MIME string.
6. تهیه ماتریس قابلیت‌ها: شاهد، سطح اطمینان، روش اعتبارسنجی و معادل پیشنهادی Linux.
7. پس از تکمیل شواهد، نوشتن specification و سپس پیاده‌سازی ماژول‌به‌ماژول همراه تست.

## نقطه شروع جلسه بعد
از [گزارش وضعیت](PROJECT-STATUS.md)، [تحلیل HTTP](HTTP-LOCAL-API-ANALYSIS.md)، [تحلیل Importها](IMPORT-TABLE-ANALYSIS.md) و [تحلیل Office/COM](OFFICE-COM-ANALYSIS.md) شروع کن. Office Automation اکنون تأیید شده؛ Import Table را تکرار نکن. گام بعدی decode فرم‌های Scan Preview و Image Tools و بررسی هدفمند COM Registry برای Word/Excel است. فرم Word Print دیگر در صف decode نیست؛ گزارش آن در [WORD-PRINT-OPTION-DFM.md](WORD-PRINT-OPTION-DFM.md) موجود است. از ادعای استخراج ZIP از سمت GitHub خودداری کن. ZIP و فایل‌های گزارش در مخزن قرار دارند، اما محتوای باینری ZIP از طریق نمایشگر متنی GitHub تحلیل نشده است.


- فرم `TfrmGScanPreview` نیز از مسیر `analysis-input/RCDATA_TFRMGSCANPREVIEW_13.bin` دریافت و decode شد: 25 component، PaintBox، ابزارهای rotate/crop/flip، انتخاب صفحه و گزینه‌های TIFF/JPEG استخراج شدند. جزئیات در [SCAN-PREVIEW-DFM.md](SCAN-PREVIEW-DFM.md) ثبت شده است. handlerهای پردازش تصویر هنوز از BPL استخراج نشده‌اند.


- فرم `TfrmImageTools` از مسیر `analysis-input/RCDATA_TFRMIMAGETOOLS_14.bin` دریافت و decode شد: مدیریت صفحات، ورود فایل/اسکن، ویرایش تصویر، زوم، قلم، Undo/Redo، درج تصاویر و تنظیمات چاپ استخراج شدند. کلاس‌های ImageEn در UI تأیید شدند. جزئیات در [IMAGE-TOOLS-DFM.md](IMAGE-TOOLS-DFM.md) است؛ رفتار handlerها هنوز باید از BPL بررسی شود.


## تکمیل تحلیل سه فرم اسکن و تصویر در 2026-11-10
- فایل `analysis-input/RCDATA_TFRMSIMPLEIMAGEEDITOR_18.bin` دریافت و decode شد: امضای `TPF0`، اندازه 11,451 بایت، 19 جزء و مصرف کامل stream بدون بایت باقی‌مانده.
- فرم `TfrmSimpleImageEditor` با عنوان «پیش‌نمایش اسکن» شناسایی شد. UI شامل PaintBox، انتخاب صفحه، Rotate، Crop، Flip افقی/عمودی، بازگشت به تصویر اصلی، گزینه TIFF/JPEG، گزینه ارسال هر صفحه به‌صورت فایل جدا و دکمه‌های تأیید/انصراف است.
- جزئیات و component inventory در [SIMPLE-IMAGE-EDITOR-DFM.md](SIMPLE-IMAGE-EDITOR-DFM.md) ثبت شد.
- مقایسه سه فرم در همان سند اضافه شد: `TfrmGScanPreview` برای پیش‌نمایش/اصلاح در مسیر اسکن، `TfrmSimpleImageEditor` برای ویرایش سبک پیش از تأیید/ارسال، و `TfrmImageTools` برای مدیریت گسترده صفحات، ورود فایل/اسکن، ویرایش و چاپ. این تقسیم نقش فعلاً برداشت مبتنی بر UI/نام‌هاست و باید با handlerها تأیید شود.
- هر سه فرم اکنون از Binary DFM با موفقیت decode شده‌اند؛ مرحله decode فرم‌های اصلی اسکن/تصویر تکمیل است. مرحله بعدی تحلیل کد handlerها در `EmwatMethods.bpl1` و استخراج قرارداد ورودی/خروجی این workflowهاست.

## نقطه ادامه به‌روز
گام بعد: ردیابی `doCommand` و Tagهای 11 تا 16 در `TfrmSimpleImageEditor`، سپس handlerهای Paint/Mouse و ثبت/ارسال؛ تطبیق آن‌ها با `TfrmGScanPreview` و `TfrmImageTools`. پس از آن specification قابل تست برای ماژول Native Linux نوشته شود. از decode دوباره این سه DFM خودداری کن مگر فایل یا شواهد جدیدی ارائه شود.


## تحلیل کد مسیرهای تصویر و اسکن در 2026-11-11

- ابزار ردیابی importها اصلاح شد تا thunkهای x86 را از روی PE import table/IAT شناسایی کند و سپس دستورهای CALL را فقط در محدوده توابع TD32 معتبر بررسی کند.
- اجرای Run 60 موفق شد: 110 import slot مرتبط با ImageGear/ImageEn، تعداد 101 thunk، نگاشت 8,411 تابع TD32 و بررسی 46,620 دستور CALL.
- مسیرهای اصلی ImageGear از روی کد تابعی تأیید شدند: Crop، RotateLeft/Right، FlipHorizontal/Vertical، SaveToFile و ScanToFile. جزئیات و آدرس‌ها در [GEAR-API-CALLS.md](GEAR-API-CALLS.md) و [IMAGE-CALL-GRAPH.md](IMAGE-CALL-GRAPH.md) ثبت شده‌اند.
- یک اشتباه مهم در helper-symbolهای قدیمی اصلاح شد: thunk `0x004AFEC8` برابر `IG_IP_rotate_multiple_90` و thunk `0x004AFED0` برابر `IG_IP_flip` است. از این پس PE import descriptor + IAT + thunk مبنای تشخیص نام API است.
- مشخص شد نام بعضی handlerهای GScan با API واقعی و مقدار direction هم‌خوانی ظاهری ندارد؛ بنابراین رفتار چرخش/برگرداندن را نباید فقط از نام دکمه یا مقدار عددی حدس زد. نسخه دقیق ImageGear و enumهای آن هنوز نامشخص‌اند.
- ImageEn نیز مسیرهای مجزایی در `TfrmImageTools` دارد: Acquire، LoadFromFileAuto، CropSel، RotateAndCrop، Flip، viewer zoom/coordinates و multi-image.
- وابستگی‌ها و روش پیاده‌سازی بومی در [Imaging-Dependency-Map.md](Imaging-Dependency-Map.md) به‌روزرسانی شده‌اند. هنوز هیچ backend بومی تصویر پیاده‌سازی نشده و parity تأیید نشده است.

### تحلیل تکمیلی Run 61 — 2026-11-11

- اجرای GitHub Actions با شناسه `43001855137` موفق شد؛ artifact `13846033438` دریافت و بررسی شد.
- متدهای `TfrmGScanPreview.SelectScanner`, `Scan`, `LoadImageToGearHandle`, `GetImagePageNumber`, `GetImgSize` و نیز `TGearImgProc.SelectScanner`, `SavePage`, `ReloadPage` با نگاشت segment-relative و confidence بالا به کد اجرایی وصل شدند.
- `TfrmGScanPreview.SelectScanner` مستقیماً `IG_save_JPEG_quality_set` و `IG_scan_pages` را فراخوانی می‌کند؛ در بدنه محدودشده فراخوانی مستقیمی به `IG_scan_source_select` دیده نشد.
- انتساب‌های قبلی `IG_scan_source_select` به `ShowCropRectangle` و `SetCurrentPage` مشکوک‌اند و تا بازبینی callsite/thunk نباید مبنای معماری اسکنر شوند.
- `Scan` و `SavePage` برای صفحات غیرجاری `IG_load_FD` و برای خروجی هر صفحه `IG_save_FD` را استفاده می‌کنند؛ هندل موقت با `IG_image_delete` آزاد می‌شود و هندل صفحه جاری حفظ می‌شود.
- جزئیات flagهای ذخیره و ABI فایل‌دسکریپتور هنوز به نسخه دقیق GEAR32PD یا آزمون کنترل‌شده نیاز دارند.
- جزئیات در [GEAR-API-CALLS.md](GEAR-API-CALLS.md) ثبت شده است.

### نقطه ادامه بعدی

1. اعتبارسنجی import thunkها و callsiteهای `IG_scan_source_select`؛ رفع انتساب‌های مشکوک.
2. استخراج و مستندسازی کامل قراردادهای callback/VMT در `TGearImgProc.SelectScanner` و کلاس/اینترفیس دستگاه.
3. شناسایی نسخه دقیق `GEAR32PD.DLL` و enum/prototypeهای همان نسخه؛ بدون این‌ها ABI فایل‌دسکریپتور را حدس نزن.
4. نوشتن specification قابل تست برای مدل تصویر بومی (pixel buffer، color model، DPI، چندصفحه‌ای، error/dirty/undo).
5. سپس پیاده‌سازی لایه‌ی SANE و مدل مستقل صفحه/تصویر؛ مسیر ImageEn باید جداگانه حفظ شود.


## Scanner interface dispatch analysis — 2026-11-11

- Run 61 artifact was unpacked and its bounded target disassembly inspected directly.
- `TfrmGScanPreview.SelectScanner` and `TGearImgProc.SelectScanner` are confirmed as distinct orchestration paths. The former sets JPEG quality, prepares an output path, invokes `IG_scan_pages` in two branches with distinct raw integer arguments, passes callback/context values through a helper, and validates the active image handle. The numeric values are not semantically decoded.
- The latter uses an interface-like object at `[self+0x28]`, dispatches through VTable offsets `+0x0C` and `+4`, stores the `IG_scan_pages` result at `[self+0x4C]`, and invokes further virtual callbacks including a dynamically obtained object's slot `+0x13C`. Method names and status meanings remain unresolved.
- Neither bounded SelectScanner body directly calls `IG_scan_source_select`; prior static caller attribution to `ShowCropRectangle` and `SetCurrentPage` remains untrusted pending raw callsite/thunk validation.
- Added [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) with evidence, confidence boundaries, a proposed native SANE-facing contract, and the next reverse-engineering tasks.
- No native scanner backend is claimed or implemented at this stage.

### Immediate next work

1. Resolve the runtime type and population path of `[TGearImgProc+0x28]` using constructor writes, RTTI and cross-references.
2. Disassemble helpers `0x004EF048`, `0x004EF1DC`, `0x004049CC`, and `0x0061D100`.
3. Revalidate `IG_scan_source_select` raw callsites and import thunk targets.
4. Identify the exact deployed `GEAR32PD.DLL` version before assigning meanings to scanner constants or implementing an ABI.

## Run 62 — scanner interface identity correction (2026-11-11)

- Run 62 (`43002726572`, artifact `13846956913`) succeeded. Four target-address traces exposed important symbol identities: `0x004EF048` = `TGearImgProc.GetEditorModalResult`; `0x004EF1DC` = `TGearImgProc.LoadPage`; `0x004049CC` = VCL `TWinControl.GetHandle`; `0x0061D100` = `TfrmGScanPreview.GetImagePageNumber`.
- Major correction: `[TGearImgProc+0x28]` is not a scanner/provider object. `SetEditorForm`'s TD32 signature explicitly accepts `DelphiInterface<IIPEditor>` and stores it at `+0x28`. RTTI confirms IID `7834c511-9078-411c-ab08-8b15ef1fd700`, implemented by `TfrmSimpleImageEditor` (VMT `0x004F046C`, interface offset `0x430`).
- The interface's `+0x0C` method is `TfrmSimpleImageEditor.GetModalRresult`; `+0x10` is `Hello`; `+0x14` is `Initial`; `+0x18` maps to `btnRegisterClick`. Thus the earlier interpretation of these virtual calls as scanner-provider dispatch was wrong and has been corrected in `SCANNER-INTERFACE-ANALYSIS.md`.
- Consequence: `TGearImgProc.SelectScanner` coordinates with the registered image editor while calling `IG_scan_pages`; the actual scanner device/provider selection path remains to be located independently. Do not design SANE around `[self+0x28]`.
- Next: trace `IIPEditor` registration/lifetime and the object passed through the `TGearImgProc` VMT slot at `+0` into `IG_scan_pages`; separately locate the true scanner source/device selection path.

## Run 63 — شناسایی اسلات صفر VMT در 2026-11-11

- دو اجرای قبلی (`43003809774` و `43003826485`) موفق شدند و هر دو artifact بررسی شد.
- VMT کلاس `TGearImgProc` در `0x004EE074` بررسی شد: اسلات `+0` = `HasError` در `0x004EF1C4`؛ اسلات `+4` = `CheckOutputParameter` در `0x004EEB60`؛ اسلات `+8` = `SelectScanner` در `0x004EF9CC`.
- در `SelectScanner` مقدار بازگشتی اسلات `+0` مستقیماً به‌عنوان یکی از آرگومان‌های `IG_scan_pages` push می‌شود. بدنه `HasError` فیلد `[self+0x24]` را بررسی می‌کند و در صورت غیرتهی بودن، متد VTable `+0x0C` شیء ذخیره‌شده در آن را صدا می‌زند.
- بنابراین `[self+0x24]` یک مرجع مستقل و هنوز ناشناخته است؛ نباید آن را با `IIPEditor` تأییدشده در `[self+0x28]` یکی دانست.
- workflow گسترش یافت تا constructor، `HasError`، `GetParentHandle`، `ShowEditor`، `SetCurrentPage` و `TfrmGScanPreview.ShowCropRectangle` را نیز در CI ردیابی کند.
- جزئیات و مرز اطمینان در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد. هنوز هیچ backend اسکنر بومی پیاده‌سازی یا ادعای تکمیل نشده است.

### گام بعدی
1. ردیابی همه writeها و lifetime شیء `[TGearImgProc+0x24]`.
2. بازسازی جداگانه ترتیب آرگومان‌های `IG_scan_pages`؛ بدون حدس درباره prototype یا enumها.
3. بازبینی واقعی callsiteهای `IG_scan_source_select` در دو مسیر `SetCurrentPage` و `ShowCropRectangle`.


## Run 64 — تشخیص مقدار عبوری از HasError

- VMT اسلات صفر TGearImgProc به HasError در 0x004EF1C4 می‌رسد؛ این متد در صورت تهی بودن فیلد +0x24 مقدار صفر برمی‌گرداند و در غیر این صورت متد +0x0C شیء رابط ذخیره‌شده در آن فیلد را فراخوانی کرده و نتیجه را بدون تغییر برمی‌گرداند.
- در SelectScanner مقدار برگشتی HasError دقیقاً به‌عنوان یکی از آرگومان‌های IG_scan_pages push می‌شود. بنابراین این مقدار یک callback نیست؛ خروجی یک interface method ناشناخته است.
- فیلد +0x24 مستقل از IIPEditor تأییدشده در +0x28 است. نوع، محل مقداردهی و معنای خروجی آن هنوز مشخص نیست.
- آدرس GetParentHandle در workflow اصلاح شد: آدرس درست 0x004EF1B4 است، نه 0x004EE1B4.
- تحلیل هنوز ایستا است؛ prototype دقیق GEAR و معنی آرگومان‌ها بدون نسخه دقیق DLL/SDK قابل اعلام نیست.

### Run 68 — اصلاح تحلیل interface و VMT

- اجرای Run 68 (43005618825) موفق شد؛ artifact 13847708592 بررسی شد.
- VMT کلاس TGearImgProc تأیید می‌کند: +0x00=HasError، +0x04=CheckOutputParameter و +0x08=SelectScanner.
- HasError فیلد +0x24 را می‌خواند و در صورت غیرتهی بودن، متد +0x0C شیء ذخیره‌شده را فراخوانی می‌کند. نتیجه آن در آرگومان‌های IG_scan_pages مصرف می‌شود؛ نوع شیء هنوز مشخص نیست.
- بدنه TfrmSimpleImageEditor.GetModalRresult به vcl230.bpl!TWinControl.GetHandle می‌رسد؛ بنابراین نباید صرفاً از روی نام متد نتیجه گرفت که ModalResult برمی‌گرداند.
- Initial پردازشگر را در فیلد +0x408 ویرایشگر ذخیره می‌کند. همچنین مشخص شد SetEditorForm از VTable رابط IIPEditor در offset +0x20 هم استفاده می‌کند؛ dump قبلی فقط تا +0x18 را نشان می‌داد.
- ابزارها اصلاح شدند تا ۱۲ slot از VTable رابط و VMT کلاس TfrmScanError را بررسی کنند و بدنه متدهای مرتبط TGearImgProc را کامل‌تر disassemble کنند.

گام بعد: شناسایی slot +0x20 رابط IIPEditor، بررسی VMT فرم TfrmScanError و تعیین دقیق آرگومان‌های IG_scan_pages بدون حدس درباره ABI.


## Run 69 — اصلاح نسبت‌دادن IIPEditor به فیلدهای TGearImgProc

- تحلیل کامل ShowEditor نشان داد آرگومان EDX در offset +0x28 ذخیره می‌شود و سپس متدهای مجازی +0x04 و سایر slotها روی همان شیء فراخوانی می‌شوند.
- SetEditorForm با امضای DelphiInterface<IIPEditor>، آرگومان خود را در offset +0x34 ذخیره می‌کند؛ بنابراین نتیجه قبلی که +0x28 را IIPEditor می‌دانستیم پس گرفته شد.
- SelectScanner نیز +0x34 را صفر می‌کند و سپس روی شیء +0x28 متدهای VTable +0x0C و +0x04 را اجرا می‌کند. پس dispatchهای آن مسیر متعلق به IIPEditor نیستند.
- RTTI مربوط به IIPEditor و پیاده‌سازی آن توسط TfrmSimpleImageEditor همچنان معتبر است؛ فقط انتساب فیلد +0x28 به آن interface اشتباه بود.
- برای حل تعارض، CI اکنون تمام referenceهای displacementهای +0x28 و +0x34 را استخراج می‌کند و TImageProcessor را هم در کشف VMT بررسی می‌کند. SavePage نیز +0x34 را در مقایسه عددی می‌خواند؛ پس معنای نهایی این فیلد تا تکمیل cross-referenceها قطعی اعلام نمی‌شود.

گام بعد: شناسایی کلاس شیء +0x28، callerهای ShowEditor، و حل lifecycle/نوع فیلد +0x34.


## Run 70 — تأیید فراخوانی‌های واقعی IG_scan_source_select

- artifact اجرای 43006403083 نشان داد دو callsite مورد اختلاف واقعاً به thunk تابع IG_scan_source_select در 0x004AFF28 و IAT برابر 0x00630CE8 می‌رسند.
- در TfrmGScanPreview.ShowCropRectangle (ورودی صحیح 0x0061E3C8)، Handle پنجره از TWinControl.GetHandle گرفته و به IG_scan_source_select داده می‌شود. آدرس قبلی 0x0061D3C8 اشتباه بود و workflow اصلاح شد.
- در TGearImgProc.SetCurrentPage، خروجی VMT slot +0 یعنی HasError به IG_scan_source_select داده می‌شود.
- بنابراین دو مسیر انتخاب منبع اسکنر تأیید شدند: یکی با HWND فرم و دیگری با خروجی dispatch داخلی Gear. معنی دقیق آرگومان دوم تا بازیابی prototype نسخه دقیق GEAR32PD مشخص نیست.

گام بعد: شناسایی شیء +0x28، تحلیل helperهای 0x004F0258 و 0x0045574C و بازیابی ABI واقعی IG_scan_source_select.


## Run 71 — اصلاح نقشه فیلدهای Gear و تشخیص mapper وضعیت

- اسکن کامل فیلدها نشان داد +0x34 وضعیت صفحه جاری است: تابع 0x004EFF94 ورودی را با 1 و مقدار +0x30 مقایسه می‌کند و در +0x34 ذخیره می‌کند؛ SavePage و ReNewPageCount نیز آن را می‌خوانند.
- بنابراین فرض Run 69 که +0x34 محل ذخیره IIPEditor است پس گرفته شد. نام/امضای TD32 برای 0x004EFF94 با رفتار machine code سازگار نیست و تا بررسی callerها قابل اتکا نیست.
- +0x30 به احتمال زیاد تعداد/حداکثر صفحات است. +0x28 شیء پردازشگر/زمینه‌ای است که ShowEditor آن را مقداردهی می‌کند و SelectScanner از slotهای +0x0C و +0x04 آن استفاده می‌کند؛ کلاس runtime هنوز مشخص نیست. VMT scan برای TImageProcessor در همین BPL کاندیدایی پیدا نکرد.
- 0x004EF048 با وجود نام TD32 به‌عنوان GetEditorModalResult، در واقع DL را به ثابت‌های 0، 0x80028، 0x15 و 2 نگاشت می‌کند و برای سایر مقادیر صفر می‌دهد؛ این تابع مستقیماً ModalResult یا IIPEditor را نمی‌خواند.
- اسکن‌های جدید +0x30 و +0x38 و disassembly کامل ReNewPageCount و SaveCPinMultiPageFile به CI اضافه شدند.

گام بعد: پیدا کردن callerهای 0x004EFF94، تعیین نوع واقعی شیء +0x28 و تحلیل helperهای 0x004ECF30 و 0x004F0258.
