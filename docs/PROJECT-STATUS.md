# وضعیت پروژه EMWAT-Linux
آخرین به‌روزرسانی: 2026-11-14

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

### Run 77 — بازیابی ترتیب آرگومان‌های IG_scan_pages

- بدنه کامل `TGearImgProc.SelectScanner` در `0x004EF9CC` ترتیب چهار آرگومان فراخوانی `IG_scan_pages` در `0x004EFA96` را مشخص می‌کند.
- آرگومان اول HWND است؛ از slot مجازی +0x0C رابط IIPEditor در فیلد +0x24 به دست می‌آید.
- آرگومان دوم مقدار path-like است که از slot +0x0C آبجکت جداگانه +0x28 گرفته و از helper رشته‌ای `0x004012E0` عبور می‌کند؛ نوع pointer و encoding هنوز مشخص نیست.
- آرگومان سوم کد فرمت خروجی است که mapper در `0x004EF048` تولید می‌کند؛ نام ثابت‌های فرمت هنوز ناشناخته است.
- آرگومان چهارم یک byte از `[EBP+8]` است که zero-extend می‌شود؛ احتمالاً flag مربوط به UI/control است، اما معنای دقیقش به caller وابسته است.
- مقدار برگشتی IG_scan_pages در `[TGearImgProc+0x4C]` ذخیره و سپس از مسیر CheckOutputParameter بررسی می‌شود.
- امضای TD32 برای SelectScanner پارامترها را جا انداخته است: در machine code، EDX به BL، ECX به selector byte و آرگومان stack در `[EBP+8]` خوانده می‌شود؛ مسیر داخلی از طریق VMT slot +8 با EDX=1 دوباره وارد همین تابع می‌شود. معنی دقیق flag و قرارداد caller هنوز نیازمند تأیید است.
- شش trace مربوط به اسلات‌های VMT والد فرضی در Run 76 کد اجرایی معتبر نشان ندادند؛ برای شناسایی کلاس والد استفاده نمی‌شوند.

### Run 78 — TScanCommand state-machine evidence (static trace)

- The TD32-derived class map identifies `TScanCommand` with candidate instance size `0x40`; its VMT candidate is not structurally valid, so virtual-slot mapping remains unresolved.
- `TScanCommand.DoRequest` writes byte field `[self+0x28]` with states `1`, `2`, and `3` along distinct request paths.
- `TScanCommand.HasError` first checks byte `[self+0x29]`; when enabled, it queries the object/interface stored at `[self+0x20]` (including virtual slot +0x10) and calls helper `0x004ECFC8`. It then writes state `2` when the nested error check is true, otherwise state `4`.
- Helper `0x004ECFC8` checks a non-null interface at `[object+0x10]`, calls the object's VMT slot +0x04 to obtain an output value, then passes that value to a Boolean helper. This is consistent with a nested error/output validation path, but exact interface and helper semantics are not named.
- The trace target used for `GetNextPage` began inside the procedure rather than at a verified entry boundary; no behavioral conclusion is drawn from that partial disassembly. Run 79 adds wider context traces around constructor, DoRequest, GetNextPage, and HasError.
- No SANE implementation or scanner ABI emulation has been added yet.

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


## Run 72 — callerها، شیء پردازشگر و page setter

- اجرای 43007155812 موفق شد و گزارش callerها نشان داد 0x004EFF94 در چهار مسیر با عدد صفحه فراخوانی می‌شود: SaveCPinMultiPageFile، Flip، TfrmSimpleImageEditor.doCommand و Finalization. بنابراین امضای TD32 که آن را DelphiInterface<IIPEditor> نشان می‌دهد با ABI واقعی سازگار نیست؛ رفتار کد یک setter/update صفحه است.
- بدنه 0x004EFF94 ورودی را بین 1 و [self+0x30] محدود می‌کند، در +0x34 ذخیره می‌کند و سپس متد +0x20 شیء +0x28 را صدا می‌زند.
- شیء +0x28 یک object دارای VMT و lifecycle است؛ در SaveCPinMultiPageFile متد +0x1C آن اجرا و سپس reference آزاد/جایگزین می‌شود. TImageProcessor یک سرنخ از signatureهاست، ولی VMT محلی آن در این BPL پیدا نشد.
- helper 0x004ECF30 فقط byte فیلد +4 شیء را برمی‌گرداند. تابع 0x004EF048 نیز DL را به ثابت‌های status نگاشت می‌کند و ModalResult را نمی‌خواند.
- +0x30 تعداد صفحات و +0x34 صفحه جاری هستند؛ +0x38 مقدار string/object-like دریافت‌شده از متدهای +0x28 است.
- ابزار جدید trace_td32_callers.py اضافه شد و callsiteهای مستقیم 0x004EFF94 و helperهای مهم را در CI استخراج می‌کند.

گام بعد: تعیین parent VMT در 0x004EDE18، گسترش disassembly helperهای 0x004F0258 و 0x004ECF38، و شناسایی slot +0x20 و داده +0x38.


## Run 73 — مسیر NotifyEditor و فیلد مسیر خروجی

- 0x004EF240 به‌طور قطعی TGearImgProc.NotifyEditor است، نه helper ناشناس. ReNewPageCount و setter صفحه آن را با مقدار +0x34 صدا می‌زنند.
- NotifyEditor handle تصویر در +0x10 را اعتبارسنجی می‌کند، مقدار path/string-like از +0x38 می‌گیرد و دو بار IG_save_FD را از thunk 0x004AFE98 فراخوانی می‌کند؛ سپس CheckOutputParameter را بررسی می‌کند، dirty flag را پاک می‌کند و ReloadPage/GetImageResolution را اجرا می‌کند.
- +0x38 به احتمال زیاد مسیر فایل/خروجی است و در page setter از VTable +0x20 شیء +0x28 مقدار می‌گیرد. نوع دقیق string و قرارداد FD هنوز مشخص نیست.
- helper 0x004ECF38 مقدار فیلد +8 شیء +0x28 را از طریق helper 0x00401240 به خروجی کپی می‌کند؛ helper 0x004ECF30 هم byte فیلد +4 را می‌خواند.
- بررسی header آدرس parent VMT در 0x004EDE18 با offsetهای استاندارد Delphi سازگار نبود؛ تا تحلیل بدنه slotها، آن را TImageProcessor نام‌گذاری نمی‌کنیم.

گام بعد: تحلیل بدنه slotهای parent در 0x004EDE18، شناسایی +0x28 و تعیین قرارداد IG_save_FD و path.


## Run 74 — اصلاح توابع FD و تشخیص فرمت خروجی

- thunk 0x004AFE98 تابع IG_load_FD است (IAT 0x00630D2C)؛ thunk 0x004AFEA0 تابع IG_save_FD است (IAT 0x00630D28). برداشت قبلی Run 73 درباره IG_save_FD در NotifyEditor اصلاح شد.
- SavePage در 0x004EF60B با ترتیب آرگومان‌های IG_load_FD، صفحه را از file descriptor به HIGEAR موقت می‌خواند؛ سپس در 0x004EF64E همان صفحه را با IG_save_FD و format code ذخیره می‌کند.
- NotifyEditor دو بار IG_load_FD صدا می‌زند و خروجی را در [self+0x10] قرار می‌دهد؛ صفحه اول با EDX و بار دوم صفحه 1 خوانده می‌شود.
- فیلد +0x14 آرگومان پنجم IG_save_FD یعنی lFormatType است. تابع 0x004EF048 byte انتخاب‌شده را به format constant نگاشت می‌کند؛ نام TD32 آن GetEditorModalResult گمراه‌کننده است.
- +0x38 مقدار backing path/stream است که برای بازکردن file descriptor استفاده می‌شود. معماری EMWAT برای ویرایش چندصفحه‌ای از یک page store مبتنی بر descriptor استفاده می‌کند.
- امضای عمومی توابع با مستندات Accusoft برای ImageGear v18.7/v21 تطبیق دارد، اما نسخه دقیق GEAR32PD.DLL هنوز مشخص نیست.

گام بعد: تعیین file-open flags و نوع رشته +0x38، معنی format constantها و تحلیل parent slotها.


## Run 75 — آرگومان‌های واقعی مسیر اسکن و محدودیت VMT والد

اجرای workflow با شناسه 43008058751 موفق شد؛ artifact برابر 13850020148 است.

- در TfrmGScanPreview.SelectScanner، IG_scan_pages چهار مقدار می‌گیرد: HWND از TWinControl.GetHandle، رشته/مسیر از فیلد +0x458، یکی از ثابت‌های 0x28 یا 2 و مقدار 1.
- در TGearImgProc.SelectScanner منشأ چهار آرگومان متفاوت است: خروجی VMT slot +0 یعنی HasError، مقدار رشته‌ای از آبجکت +0x28 از طریق virtual +0x0C، خروجی mapper در 0x004EF048 و byte ورودی متد.
- خروجی IG_scan_pages در مسیر Gear داخل [self+0x4C] ذخیره می‌شود؛ در مسیر Preview بلافاصله مصرف نمی‌شود.
- مقدار HasError از interface ناشناخته در [self+0x24] و slot +0x0C آن می‌آید؛ فعلاً نباید آن را HWND یا شناسه دستگاه فرض کرد.
- امضای TD32 تابع @Gear@IG_scan_pages$qqsp6HWND__pxcuio است، اما تفاوت منشأ آرگومان اول بین دو caller هنوز با prototype دقیق GEAR32PD حل نشده است.
- دو callsite تأییدشده IG_scan_source_select نیز داده‌های متفاوت می‌فرستند: مسیر Preview یک HWND واقعی و مسیر Gear خروجی slot صفر VMT را.
- شش target اسلات والد در 0x004EDE18 به محدوده‌های TD32 قابل اتکا وصل نشدند و header استاندارد Delphi هم با این آدرس سازگار نیست؛ بنابراین هنوز نمی‌توان آن را TImageProcessor نامید.

### گام بعد
1. تمام writeها و referenceهای فیلد [TGearImgProc+0x24] را استخراج و منبع interface را پیدا کنیم.
2. نوع runtime شیء [TGearImgProc+0x28] را از constructor، setter و VMT معتبر شناسایی کنیم؛ نه از parent pointer فعلی.
3. نسخه دقیق GEAR32PD.DLL یا header/import library متناظر را پیدا کنیم تا ABI دو تابع اسکن قطعی شود.
4. تا آن زمان مقادیر عددی و نوع آرگومان‌ها را نام‌گذاری نکنیم؛ backend لینوکس همچنان مستقل و مبتنی بر SANE طراحی شود.


## Run 76 — شناسایی قطعی‌تر interface فیلد +0x24 و حل HWND

اجرای 43027580174 موفق شد؛ artifact برابر 13857623235 است.

- فیلد [TGearImgProc+0x24] همان interface از نوع IIPEditor است، نه interface خطا. تابع setter در 0x004F0084 آن را با helper مدیریت interface مقداردهی می‌کند.
- در caller مربوط به TScanCommand.$bdtr، مقدار EDX با offset برابر 0x430 تنظیم و به setter داده می‌شود. این offset دقیقاً با IOffset رابط IIPEditor در TfrmSimpleImageEditor برابر است.
- caller دوم در 0x004F1151 مقدار nil را به همان setter می‌دهد؛ این با پاک‌کردن/release رابط هنگام teardown سازگار است.
- IID رابط 7834c511-9078-411c-ab08-8b15ef1fd700 و VTable آن 0x004F03D4 است؛ پیاده‌سازی در TfrmSimpleImageEditor با offset برابر 0x430 ثبت شده.
- TGearImgProc.HasError در واقع slot +0x0C رابط IIPEditor را صدا می‌زند. پیاده‌سازی متناظر در 0x004F1158 تابع TWinControl.GetHandle را اجرا و مقدار HWND را برمی‌گرداند.
- بنابراین مقدار ارسالی از Gear به IG_scan_pages و IG_scan_source_select هم HWND است؛ تفاوت قبلی فقط تفاوت مسیر دستیابی به handle بود، نه تفاوت نوع مقدار.
- فیلد +0x28 همچنان یک آبجکت جداگانه با VMT و stateهای +4/+8 است و کلاس runtime آن هنوز مشخص نشده.
- RTTI اسمی IImageProcessor هم پیدا شد، اما GUID آن صفر است و در این BPL پیاده‌سازی متناظری پیدا نشد؛ این یافته دلیل نمی‌شود +0x24 را IImageProcessor بدانیم.

### گام بعد
1. شناسایی runtime class و قرارداد virtualهای آبجکت مستقل +0x28.
2. تعیین رفتار واقعی slotهای IIPEditor در +0x10، +0x14 و +0x18؛ نام‌های TD32 برای wrapperهای Gear قابل اتکا نیستند.
3. بازیابی prototype کامل IG_scan_pages و IG_scan_source_select؛ HWND اکنون مشخص است اما آرگومان‌های دیگر و ثابت‌ها هنوز نه.
4. ادامه طراحی backend لینوکس با SANE، بدون تقلید layout و ABI ویندوز.


## Run 77 — منشأ context پردازش صفحه

در artifact اجرای موفق 43029566665 مشخص شد:

- فیلد TScanCommand+0x20 در DoRequest خوانده و به TGearImgProc.ShowEditor داده می‌شود.
- همین فیلد در GetNextPage در سه مسیر (0x004F2637، 0x004F268B و 0x004F26A9) نوشته می‌شود؛ هر سه مقدار از helper/factory در 0x004EC8B4 می‌آیند.
- ShowEditor همان pointer را در TGearImgProc+0x28 ذخیره می‌کند و از virtual slot +4 آن یک رشته می‌گیرد که به +0x38 منتقل می‌شود.
- TScanCommand.HasError از virtual slot +0x10 همین آبجکت استفاده و سپس helper 0x004ECFC8 را صدا می‌زند؛ بر اساس نتیجه، status byte در TScanCommand+0x28 را به 2 یا 4 تغییر می‌دهد.
- پس TGearImgProc+0x28 یک processing context واقعی و تولیدشده برای request/page است؛ هنوز نباید آن را با IIPEditor در +0x24 یا با interface اسمی IImageProcessor یکی دانست.

اجرای بعدی 43030170561 برای بررسی کامل GetNextPage و بدنه helperهای 0x004EC8B4 و 0x004ECFC8 اضافه شده است.


## Run 79 — بازیابی contextهای سازنده و چرخه صفحه

اجرای 43032078996 موفق شد و چهار فایل context اکنون در Artifact موجودند. نتایج قابل اتکا:

- سازنده در 0x004F21F0 ابتدا constructor پایه را از طریق 0x004EEDB4 اجرا می‌کند و نتیجه را در [self+0x04] می‌گذارد؛ سپس interface جداگانه‌ای را با 0x00404D5C می‌سازد و در +0x24 ذخیره می‌کند. این بخش با مالکیت IIPEditor در +0x24 سازگار است.
- سازنده یک شیء دیگر را از 0x004EB7F4 دریافت و در +0x34 قرار می‌دهد و سپس virtual slot +0xB8 آن را فراخوانی می‌کند؛ کلاس و معنای دقیق این dependency هنوز مشخص نیست.
- بخش معتبر GetNextPage در محدوده 0x004F25CC به بعد نشان می‌دهد state دو بایتی از +0x1D و +0x1E نگهداری می‌شود. تابع 0x004EC8B4 با دو byte mode/selector و یک مقدار موقت، context جدید می‌سازد و خروجی در +0x20 قرار می‌گیرد.
- در مسیر عادی، helper با mode byte فعلی و byte همراه آن فراخوانی می‌شود؛ در مسیر جایگزین، اگر mode برابر 2 باشد، mode ورودی به factory برابر 3 می‌شود. در مسیرهای دیگر، mode فعلی حفظ می‌شود.
- helper 0x004F29E0 از طریق 0x00401398 با پارامتر ثابت 1 اجرا می‌شود؛ اگر نتیجه مثبت باشد، byte وضعیت +0x1E به 2 تغییر می‌کند. سپس HasError فراخوانی می‌شود.
- بلوک بعدی، context را مجدداً از روی pair بایت‌های +0x1D/+0x1E می‌سازد؛ بنابراین context +0x20 به وضعیت جاری صفحه وابسته است و یک شیء ثابت برای کل عمر ScanCommand نیست.

محدودیت: traceهای نقطه‌ای 0x004F2250 و 0x004F25C0 وسط دستور/بلوک افتاده‌اند و trace HasError از 0x004F2A80 نیز هم‌ترازی کد ندارد. بنابراین از آن‌ها برای نام‌گذاری متد یا نتیجه‌گیری درباره بدنه کامل استفاده نمی‌کنیم. اجرای بعدی، traceهای هم‌تراز از 0x004F2274، 0x004F25CC، 0x004F26F2، 0x004F27C4 و 0x004F29E0 را اضافه کرده است.


## Run 80 — تحلیل dispatch چرخه ScanCommand (2026-11-11)

اجرای 43033266952 موفق شد و artifact 13861452924 بررسی شد.

- trace هم‌تراز GetNextPage از 0x004F25CC نشان می‌دهد پیش از ساخت context، یک loop مقدار byte وضعیت [self+0x1D] را از چهار ورودی/مقدار مقایسه‌شده انتخاب می‌کند؛ اگر match پیدا شود index در فیلد ذخیره می‌شود. بنابراین +0x1D صرفاً یک mode ثابت نیست و در این بخش از انتخاب بین چهار گزینه نیز استفاده می‌شود.
- پس از آن helper فراخوانی‌شده از طریق 0x00401398 با آرگومان ثابت 1 نتیجه عددی می‌دهد؛ نتیجه مثبت byte دوم [self+0x1E] را 2 می‌کند. سپس context با 0x004EC8B4 از هر دو byte ساخته و در +0x20 قرار می‌گیرد و HasError اجرا می‌شود.
- در continuation، pointer context از +0x20 به تابع 0x004F0174 داده می‌شود؛ سپس word حاصل از دو state byte در فیلدهای +0x55 و +0x57 شیء پایه [self+0x04] کپی می‌شود. پس از آن توابع 0x004F22E4 و 0x004F2B18 فراخوانی می‌شوند.
- dispatch بعدی بر اساس status byte [self+0x28] مقادیر 1 تا 4 را از هم جدا می‌کند. در شاخه status=2، context فعلی +0x20 از طریق 0x004ECE2C خوانده و مقدار خروجی به helper 0x004735C4 داده می‌شود. شاخه‌های 3 و 4 مسیرهای آماده‌سازی جدا دارند.
- مسیر dispatch سپس روی dependency ذخیره‌شده در +0x34 virtual slotهای +0xB8 و +0xB4 را اجرا می‌کند و روی context +0x20 نیز slotهای +0x08 و متدهای کمکی دیگر را فراخوانی می‌کند. نام و قرارداد این virtualها هنوز حل نشده است.
- traceهای 0x004F2274 و 0x004F29E0 هیچ دستور معتبری decode نکردند؛ بنابراین این دو آدرس را entry قطعی DoRequest یا تابع مستقل request-helper تلقی نمی‌کنیم. trace قدیمی 0x004F2250 نیز وسط دستور/epilogue افتاده است.
- trace dispatch در 0x004F27C4 فقط تا 0x004F28C0 ادامه دارد؛ برای تکمیل شاخه‌ها باید ادامه بدنه و targetهای 0x004F22E4 و 0x004F2B18 بررسی شوند.

گام بعد: trace از 0x004F2278 و 0x004F28C0، سپس تحلیل 0x004F22E4 و 0x004F2B18 و تطبیق statusها با DoRequest/HasError. تا زمان بازیابی entry واقعی، نام‌گذاری متد DoRequest و helper در محدوده‌های مبهم متوقف بماند.


## به‌روزرسانی مسیر اسکن — Run 81 (2026-11-12)
- اجرای `43036386819` موفق شد و Traceهای ادامه‌ی `0x004F22E4`، انتهای helper و cleanup بررسی شدند.
- مسیر جدید نشان می‌دهد helper در بعضی وضعیت‌ها callback record می‌سازد، آن را از `0x0044ABE4` عبور می‌دهد و اگر نتیجه 6 باشد، context را از VMT slot `+0x1C` ادامه داده و `0x004F22E4` را دوباره اجرا می‌کند؛ در غیر این صورت status داخلی را 3 می‌گذارد.
- تحلیل با جزئیات و مرزبندی اطمینان در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.
- هنوز معنای callbackها، layout رکورد و قرارداد `0x0044ABE4` مشخص نیست؛ بنابراین این بخش را نباید به‌عنوان ABI قطعی اسکنر تفسیر کرد.
- گام بعد: trace کردن callbackهای `0x004F2454` و `0x004F2474`، رکورد `0x004F2490`، dispatcher `0x0044ABE4` و مسیر exception/finally.


## اصلاح تحلیل Run 81 — شناسایی RemoveTempFiles (2026-11-12)
- نماد TD32 مشخص کرد آدرس `0x0044ABE4` تابع `Emwat.Sys.RemoveTempFiles` است، نه dispatcher مربوط به callback اسکن.
- همین تابع از `TfrmSimpleImageEditor.ToggleCropMode` نیز فراخوانی می‌شود؛ بنابراین utility مشترکی است، اما صرف نام نماد برای اثبات حذف فایل کافی نیست.
- آدرس‌های `0x004F2454`، `0x004F2474` و `0x004F2490` disassembly معتبر x86 ندارند و نباید callback یا ABI اجرایی تلقی شوند.
- در مسیر ScanCommand فقط می‌توان گفت نتیجه تابع با عدد 6 مقایسه می‌شود؛ در صورت برابری، context از VMT slot `+0x1C` ادامه می‌یابد و helper `0x004F22E4` دوباره اجرا می‌شود. معنای عدد 6 هنوز نامشخص است.
- Traceهای بعدی برای شناسایی قرارداد آرگومان‌ها و helperهای داخلی RemoveTempFiles به workflow افزوده شدند.


## Run 82 — بازبینی RemoveTempFiles (2026-11-12)
- اجرای `43157168446` موفق شد؛ artifact `13916526235` بررسی شد.
- بدنه `0x0044ABE4` به‌جای API حذف فایلِ قابل مشاهده، componentهای یک object را با `TComponent.GetComponentCount/GetComponent` پیمایش می‌کند؛ Run 83 نشان داد که componentهای منطبق با یک کلاس global، متن می‌گیرند و virtual slot `+0x13C` اجرا می‌شود.
- در همان مسیر، thunkهای `0x00404894` و `0x00404E34` به `TControl.SetText` و `TCustomForm.SetFormStyle` resolve شدند؛ virtual slotهای `+0x94` و `+0x13C` نیز اجرا می‌شوند.
- بنابراین برداشت «قطعاً پاک‌سازی فایل موقت» فعلاً تأیید نشده است؛ ممکن است نام TD32 قدیمی/گمراه‌کننده باشد یا عملیات نهایی از virtual/helper خارج از image انجام شود.
- در caller اسکن، return value با 6 مقایسه می‌شود؛ معنای آن همچنان نامشخص است.
- traceهای تکمیلی انتهای تابع، helperهای string/array/exception و callerهای دیگر به workflow افزوده شدند.
- جزئیات و محدودیت استنباط در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.


## Run 83 — قرارداد داخلی helper عمومی VCL (2026-11-12)
- اجرای `43158235892` موفق شد؛ artifact `13917012048` بررسی شد.
- `0x0044ABE4` componentهای یک container را با `TComponent.GetComponentCount/GetComponent` پیمایش می‌کند؛ برای هر مورد، `System.IsClass` را با کلاس global در `0x62FE28` اجرا می‌کند.
- در صورت match، مقدار open-array را به `TControl.SetText` می‌دهد؛ سپس `TCustomForm.SetFormStyle(3)` و virtual slot `+0x13C` اجرا می‌شوند. مقدار خروجی از همین virtual slot می‌آید.
- helperهای RTL به `System.IsClass`، `TObject.Free`، `System.AddRefArray` و `System.UStrAddRef` resolve شدند.
- بنابراین نام TD32 یعنی `RemoveTempFiles` رفتار واقعی تابع را به‌تنهایی توصیف نمی‌کند؛ حذف فایل از بدنه قابل مشاهده اثبات نشده است.
- در ScanCommand، مقدار 6 با نتیجه virtual slot مقایسه می‌شود؛ معنای این status و کلاس هدف هنوز نامشخص است.
- جزئیات در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.


## Run 84 — شناسایی helper پنجرهٔ محاوره‌ای (2026-11-12)
- اجرای `43159971265` موفق شد؛ artifact `13917817103` بررسی شد.
- تفسیر قبلی TD32 برای `0x0044ABE4` اصلاح شد: این تابع فایل موقت حذف نمی‌کند؛ componentهای فرم را می‌گردد، متن برخی کنترل‌ها را تنظیم می‌کند، `TCustomForm.SetFormStyle(3)` را اجرا می‌کند و از virtual slot `+0x13C` نتیجهٔ modal می‌گیرد.
- importهای VCL وجود `TCustomForm.ShowModal` را تأیید می‌کنند؛ slot مذکور با اطمینان بالا همان ShowModal است. `3=fsStayOnTop` و `6=mrYes`.
- callerهای Scan Error، ToggleCropMode و ScanCommand از انتخاب Yes برای تغییر state/ادامهٔ مسیر استفاده می‌کنند.
- در پورت Linux این بخش باید به dialog abstraction تبدیل شود، نه فایل‌پاک‌کن.
- جزئیات و شواهد در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.


## Run 85 — جداسازی callerهای اسکن و helperهای عمومی (2026-11-12)
- اجرای `43160920858` موفق شد؛ artifact `13917599363` بررسی شد.
- helper عمومی با `System.IsClass`، `TComponent.GetComponentCount/GetComponent`، `TControl.SetText` و `TCustomForm.SetFormStyle` کار می‌کند؛ کلاس مرجع runtime در `0x0023D27E` خارج از image است و هنوز نامش معلوم نیست.
- callerهای جدید modal در Scan Error، ToggleCropMode و TIFF بررسی شدند؛ نتیجهٔ 6 در callerهای مشخص‌شده به‌عنوان شرط ادامه/تغییر state مصرف می‌شود.
- نقشهٔ importها دو caller مستقل برای `IG_scan_pages` نشان می‌دهد: Preview و GearImgProc. همچنین دو caller مستقل `IG_scan_source_select` در `ShowCropRectangle` و `SetCurrentPage` ثبت شده‌اند.
- گام بعدی: trace آرگومان‌ها و stateهای هر چهار callsite اسکن، بدون فرض یکسان بودن دو مسیر.


## Run 86 — call graph قطعی اسکنر
- اجرای `43162207819` موفق شد و artifact بررسی شد.
- دو orchestrator مستقل برای `IG_scan_pages` شناسایی شد: Preview (دو call) و GearImgProc (یک call).
- دو callsite مستقل `IG_scan_source_select` در Preview.ShowCropRectangle و GearImgProc.SetCurrentPage تأیید شد.
- گام بعدی: trace کامل بدنهٔ متدهای `SelectScanner` و ثبت stack/arguments هر call، به‌خصوص دو فراخوانی Preview.


## Run 87 — استخراج state و چرخهٔ ذخیره/بارگذاری تصویر
- اجرای `43163883733` موفق شد؛ trace کامل متدهای GearImgProc بررسی شد.
- ShowEditor context را در +0x28 و backing path/descriptor را در +0x38 تنظیم می‌کند؛ +0x34 صفحهٔ فعال، +0x30 تعداد صفحات و +0x54 وضعیت dirty است.
- SetCurrentPage بازهٔ صفحه را اعتبارسنجی می‌کند، در صورت dirty بودن امکان SaveToFile را از طریق modal Yes می‌دهد، سپس context virtual +0x20 را برای صفحهٔ جدید فراخوانی و NotifyEditor را اجرا می‌کند.
- NotifyEditor با IG_load_FD صفحه را از backing descriptor به HIGEAR فعال reload می‌کند؛ SavePage روی همهٔ صفحات loop می‌زند و برای صفحات غیرفعال HIGEAR موقت می‌سازد؛ SaveToFile و ScanToFile دو مسیر جدا هستند.
- RotateLeft/Right dirty state را تغییر می‌دهند، اما عملیات pixel-level در helperهای خارجی/virtual انجام می‌شود و هنوز ABI آن‌ها مشخص نیست. نام قبلی Crop برای تابع 0x004EEDB4 تأیید نشد؛ بدنه بیشتر شبیه constructor یک context object است.
- تحلیل تفصیلی و مرزهای اطمینان در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.
- گام بعد: resolve کردن helperهای rotation و context، callerهای آن‌ها، و تابع‌های GEAR مربوط به save/load/scan؛ سپس تبدیل این یافته‌ها به قرارداد ماژول مستقل image document در Linux.


## Run 88 — تفکیک rotation و page refresh
- اجرای `43164659373` با موفقیت کامل شد؛ artifact `13919407916` بررسی شد.
- importهای مهم ImageGear به‌صورت قطعی‌تر به thunkها متصل شدند: `IG_image_delete`، `IG_image_is_valid`، `IG_IP_rotate_multiple_90`، `IG_image_dimensions_get` و `IG_page_count_get`.
- نکتهٔ اصلاحی: متد TD32 با نام `Rotate90` مستقیماً pixelها را rotate نمی‌کند؛ page count را از backing document می‌خواند و context virtual slot صفر را صدا می‌زند. چرخش واقعی در `RotateLeft` از طریق `IG_IP_rotate_multiple_90` انجام می‌شود و سپس ReloadPage/refresh resolution و dirty flag رخ می‌دهد.
- این تفکیک برای طراحی native مهم است: page/document refresh، pixel transform و lifecycle آزادسازی image handle باید APIهای جدا باشند.
- جزئیات و disassembly در [SCANNER-INTERFACE-ANALYSIS.md](SCANNER-INTERFACE-ANALYSIS.md) ثبت شد.
- گام بعد: تکمیل قرارداد dimensions/page-count/delete و context virtualها، سپس تثبیت مدل Document/Page/PixelBuffer و شروع پیاده‌سازی native.


## Run 89 — ImageGear lifecycle و قرارداد اولیهٔ Document/Page
- اجرای `43165458320` موفق شد؛ artifact `13919863021` بررسی شد.
- `IG_image_dimensions_get` در `ReloadPage` با HIGEAR و سه output pointer در offsetهای `+0x40`، `+0x3C` و `+0x44` فراخوانی می‌شود؛ معنای دقیق هر خروجی هنوز قطعی نیست.
- `IG_page_count_get` علاوه بر `Rotate90` در `SaveToFile` و مسیرهای Preview نیز استفاده می‌شود؛ بنابراین page count بخشی از metadata سند است، نه عملیات چرخش پیکسل.
- `IG_image_delete` در مسیرهای teardown/replacement در Preview و همچنین `NotifyEditor`، `PaintCanvas` و `SavePage` دیده می‌شود؛ این موضوع اهمیت lifecycle/ownership روشن را تأیید می‌کند.
- `IG_image_is_valid` پیش از چند عملیات reload، metadata، paint و save بررسی می‌شود.
- سند معماری اولیهٔ مستقل از ImageGear در [NATIVE-IMAGE-DOCUMENT-DESIGN.md](NATIVE-IMAGE-DOCUMENT-DESIGN.md) ایجاد شد؛ شامل Document/Page/PixelBuffer، مرز API، ownership، تست‌های parity و سؤال‌های باز.
- گام بعد: resolve کردن قرارداد سه خروجی dimensions و context virtualها؛ سپس ساخت اسکلت ماژول native و تست‌های واحد برای transformهای pixel بدون وابستگی به GEAR.

## پیاده‌سازی اولیه کشف اسکنر در Linux (2026-11-12)

- رابط مستقل ScannerBackend و ساختار ScannerDevice در `native/include/emwat/scanner.hpp` اضافه شد؛ لایه UI و مدل سند تصویر به API اختصاصی SANE وابسته نیستند.
- پیاده‌سازی SaneScannerBackend در `native/src/sane_scanner.cpp` از `sane_init`، `sane_get_devices` و `sane_exit` استفاده می‌کند و شناسه، سازنده، مدل و نوع دستگاه را برمی‌گرداند.
- چرخه عمر SANE در هر درخواست کشف دستگاه محدود و با mutex سریال شده است؛ خطاهای init و discovery به ScannerError تبدیل می‌شوند.
- تست قرارداد backend با fake backend اضافه شد. CI اکنون `libsane-dev` و `pkg-config` را نصب و کتابخانه SANE را در build لینک می‌کند.
- **محدودیت فعلی:** این milestone فقط کشف و فهرست‌کردن دستگاه‌هاست؛ هنوز تنظیم گزینه‌ها، شروع اسکن، خواندن فریم‌ها، لغو اسکن و تحویل صفحه به ImageDocument پیاده‌سازی نشده‌اند. این‌ها باید در گام بعد و با fake acquisition tests و تست سخت‌افزار واقعی اضافه شوند.

## دریافت اولین فریم و تنظیمات اسکن از SANE (2026-11-12)

- قرارداد `ScannerBackend` متد `scan_one(device_id, options)` دارد که یک `ImagePage` برمی‌گرداند و `get_capabilities(device_id)` قابلیت‌های هر دستگاه را گزارش می‌کند.
- قابلیت‌یابی، فهرست حالت‌های رنگ و منبع را از string-listهای SANE و رزولوشن را از range یا word-list descriptor استخراج می‌کند؛ گزینه‌های inactive یا غیرقابل تشخیص به‌عنوان قابلیت قابل انتخاب گزارش نمی‌شوند. `ScanOptions` سه تنظیم اختیاری دارد: رزولوشن برحسب DPI، حالت اسکن و منبع کاغذ.
- پیاده‌سازی SANE دستگاه را باز می‌کند، در صورت درخواست گزینه‌های `resolution`، `mode` و `source` را از طریق descriptorهای فعال و قابل تنظیم SANE اعمال می‌کند، سپس اسکن را شروع می‌کند، پارامترهای فریم را می‌خواند و داده‌ها را در بلوک‌های 64 KiB دریافت می‌کند.
- نام گزینه‌های SANE برای رزولوشن/حالت/منبع به‌ترتیب `resolution`، `mode` و `source` است؛ اگر دستگاه گزینه‌ای را ارائه نکند یا نوع/قابلیت آن ناسازگار باشد، درخواست با `ScannerError` روشن رد می‌شود. انتخاب مقادیر مجاز رشته‌ای و محدودیت‌های سخت‌افزاری نهایی به backend SANE واگذار می‌شود.
- خروجی فعلی محدود به Gray8 و RGB8 است؛ ابعاد متغیر، عمق‌های دیگر، فرمت‌های دیگر و فریم ناقص با خطای روشن رد می‌شوند.
- سقف حافظه هر اسکن 1 GiB است؛ طول داده دریافتی، stride و اندازه فریم بررسی می‌شوند. در خطاهای حین دریافت، اسکن لغو می‌شود و handle/session به‌صورت RAII بسته می‌شوند.
- تست fake backend اکنون مسیر قرارداد دریافت یک ImagePage و خطای اسکن را هم پوشش می‌دهد.
- **محدودیت‌های زمان ثبت این مرحله:** اسکن چندفریمی یا duplex، خطوط با ارتفاع نامعلوم، عمق 16-bit، lineart و لغو از UI هنوز پشتیبانی نمی‌شوند. DPI در مرحله بعد از اعمال تنظیمات از گزینه‌های فعال SANE خوانده می‌شود؛ مقدار درخواستی به‌عنوان DPI واقعی ثبت نمی‌شود.


## ثبت DPI واقعی خروجی اسکن (2026-11-12)

- پس از اعمال تنظیمات اختیاری و پیش از شروع فریم، backend مقدار واقعی گزینه‌های فعال SANE را با `SANE_ACTION_GET_VALUE` می‌خواند.
- در دستگاه‌هایی که `x-resolution` و `y-resolution` جدا دارند، هر محور جداگانه ثبت می‌شود؛ اگر فقط یکی قابل خواندن باشد همان مقدار برای هر دو محور استفاده می‌شود. در دستگاه‌های دارای گزینهٔ عمومی `resolution`، مقدار آن برای هر دو محور ثبت می‌شود.
- مقدار ناموجود، غیرفعال، نامعتبر یا غیرقابل خواندن به‌صورت `nullopt` باقی می‌ماند؛ DPI از مقدار درخواستی یا مقدار پیش‌فرض حدس زده نمی‌شود.
- تست قرارداد ScannerBackend ثبت DPI در `ImagePage` را پوشش می‌دهد. خواندن مقدار از دستگاه واقعی همچنان به سخت‌افزار/درایور SANE وابسته است.


## محدودسازی ورودی قابلیت‌های SANE (2026-11-12)

- خواندن فهرست قابلیت‌های driver محدود شد: حداکثر 256 مقدار رشته‌ای و حداکثر 256 نویسه برای هر مقدار پذیرفته می‌شود.
- word-list رزولوشن حداکثر تا 4096 ورودی بررسی می‌شود؛ مقادیر نامعتبر، غیرمثبت یا بزرگ‌تر از 100000 DPI کنار گذاشته می‌شوند.
- بازه رزولوشن نیز باید محدود، مثبت و حداکثر 100000 DPI باشد. مقادیر discrete مرتب و تکراری‌ها حذف می‌شوند.
- هدف، محدودکردن مصرف منابع و جلوگیری از انتشار داده‌های نامعتبر driver در لایه قابلیت‌هاست؛ این محدودیت‌ها جایگزین اعتبارسنجی نهایی خود backend نمی‌شوند.


## Run 90 — بازتعریف دامنه محصول بر اساس گردش‌کار واقعی الماس گام (2026-11-12)

- کاربر توضیح داد EMWAT در استفاده اصلی، سرویس/واسط محلی متصل به اتوماسیون تحت وب الماس گام است؛ هنگام ایجاد یا ویرایش نامه، Word را باز می‌کند، اطلاعات و قالب تنظیم‌شده در الماس گام (مانند موضوع، شماره، امضاکنندگان، سربرگ، لوگو، فونت، حاشیه و محل امضا) را در سند اعمال می‌کند و کاربر متن نامه را ویرایش می‌کند.
- طبق توضیح کاربر، پس از بستن Word فایل نهایی به الماس گام برمی‌گردد و ذخیره نهایی در خود الماس گام انجام می‌شود. جزئیات اینکه بدون Save نیز تغییرات ارسال می‌شوند، با قطعیت پایین‌تر بیان شده و باید با آزمایش کنترل‌شده تأیید شود.
- کاربر تأیید کرد بعضی نامه‌ها کاملاً تصویری هستند؛ اما ساخت و ویرایش آن‌ها، از جمله حذف/افزودن صفحات، هنوز از تجربه مستقیم کاربر تأیید نشده است. بنابراین موتور اسکن و تصویر حفظ می‌شود.
- این شناخت، اولویت پروژه را تغییر می‌دهد: ابتدا باید قرارداد واقعی مرورگر ↔ سرویس محلی، dispatch متدها و انتقال فایل استخراج شود؛ سپس نمونه انتها‌به‌انتها برای نامه متنی و LibreOffice ساخته شود. قابلیت‌های تصویر در دامنه باقی می‌مانند.
- شواهد ایستای bridge در EmwatService.exe نشان می‌دهد JavaScript پیام message را دریافت می‌کند، event.data را با POST به 127.0.0.1 و مسیر invoke می‌فرستد و responseText را با postMessage به source/origin اولیه بازمی‌گرداند. این شواهد قرارداد کامل payload یا مدیریت فایل را ثابت نمی‌کنند.
- سند تفصیلی [PRODUCT-WORKFLOW-ANALYSIS.md](PRODUCT-WORKFLOW-ANALYSIS.md) ایجاد شد و README با هدف واقعی پروژه و اولویت‌های جدید هم‌راستا شد.
- **وضعیت پیاده‌سازی:** این مرحله مستندسازی و بازتنظیم اولویت‌هاست؛ هنوز سرویس Linux سازگار با پروتکل واقعی الماس گام یا چرخه بازگشت سند پیاده‌سازی نشده است.
- **گام بعد:** تحلیل دقیق متدهای قابل فراخوانی در EmwatMethods.bpl1 و اتصال نام/آرگومان/نوع خروجی آن‌ها به bridge؛ سپس طراحی آزمایش runtime امن با یک نامه ساختگی.


## Run 91 — شناسایی connector و مدل XML گردش‌کار Word (2026-11-12)

- تحلیل RTTI/symbolهای EmwatMethods.bpl1 کلاس Emwatconnector.TEditWordDocument.PerformMethod، dispatcher عمومی Emwatmethod.TEmwatMethod.Invoke/PerformMethod و Wordviewer.OpenDoc را نشان داد.
- مدل request در Wordrequestxml دارای Worddocument با Body، Fields، Optionalattributes، Permission، Requestedtypes، Settings، Status و ViewMode است؛ Field دارای Id، Concator، Mimetype، Separator و Encryption؛ Style دارای Align، FontName، FontSize، FontStyle و Valign است.
- مدل response در Wordresponsexml دارای Status، ErrorCode و Returntypes است؛ نوع return نیز Encryption و Mimetype دارد.
- در Wordviewer متدهای LoadDocument، PrepareDocument، FillField، FillImageField، AddImagesToDoc، SetFieldValue، GetFieldValue و دیگر helperهای سند دیده شدند.
- وجود SilentSaveEmwatDoc، OnTmrAutoSave، WordAppDocumentBeforeClose و WordAppDocumentBeforeSave نشان می‌دهد lifecycle ذخیره‌سازی/بسته‌شدن در EMWAT مدیریت می‌شود؛ اما ارسال قطعی تغییرات ذخیره‌نشده یا زمان دقیق بازگشت به الماس گام هنوز runtime-validated نیست.
- connectorهای TEditExcelWorkBook، TCompareWordDocument، TFaxDocument، TImageEdition و TScanDocument نیز در RTTI دیده شدند؛ این موضوع حفظ معماری چندماژوله Word/Excel/scan/image/fax را تقویت می‌کند.
- سند [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) ایجاد و به README و تحلیل گردش‌کار اضافه شد.
- **گام بعد:** اتصال این نمادها به handlerهای واقعی و استخراج schema XML/dispatch از بدنه کد/نمونه runtime؛ سپس ثبت trace پاک‌سازی‌شده از یک نامه آزمایشی.


## Run 92 — تکمیل ساختار collectionهای Word XML (2026-11-12)

- RTTI تکمیلی Wordrequestxml وجود collectionهای Fields و Settings را نشان می‌دهد؛ Word Body نیز metadata مربوط به Encryption دارد.
- ParamsToXML به‌عنوان تبدیل dictionary پارامترها به XML در unit Emwatmethod ثبت شد.
- مدل‌های Field و Return Type هر دو metadataهای MIME type و Encryption دارند؛ این یافته احتمال وجود payloadهای غیرمتنی/رمزشده را برای برخی فیلدها مطرح می‌کند، اما encoding و الگوریتم هنوز ناشناخته است.
- سند [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) با این جزئیات تکمیل شد.
- **گام بعد:** استخراج بدنه/نمونه‌های واقعی XML و mapping متدهای connector؛ سپس runtime trace کنترل‌شده. تا آن زمان هیچ schema یا رمزنگاری فرضی در کد production پیاده‌سازی نمی‌شود.


## Run 93 — مشاهده runtime اولین درخواست invoke از الماس گام (2026-11-12)

- کاربر در Firefox درخواست واقعی با Method برابر POST را مشاهده کرد.
- URL کپی‌شده: `http://127.0.0.1:1984/?invoke=83011`.
- صفحه caller / Referer گزارش‌شده: `automation.bsi.ir/secretariat/ClientSingleton.do`.
- این شاهد runtime تأیید می‌کند که حداقل یک درخواست عملیاتی از صفحه ClientSingleton به endpoint ریشه سرویس محلی روی پورت 1984 ارسال می‌شود.
- مقدار `83011` فعلاً فقط مقدار مشاهده‌شده پارامتر invoke است؛ نقش آن (شناسه متد، شناسه درخواست یا مقدار دیگر) نامشخص است.
- هنوز Request Body، Content-Type، پاسخ و معنای عملیات استخراج نشده‌اند؛ بنابراین هیچ wire schema یا dispatch mapping بر اساس این مقدار حدس زده نمی‌شود.
- سند [HTTP-LOCAL-API-ANALYSIS.md](HTTP-LOCAL-API-ANALYSIS.md) با این مشاهده runtime تکمیل شد.
- **گام بعد:** دریافت Request Body و Content-Type و Response از همان درخواست، با حذف کامل Cookie/Authorization/token و محتوای محرمانه؛ سپس اتصال payload به متدهای RTTI در EmwatMethods.bpl1.


## Run 94 — تحلیل HAR و استخراج نمونه EditWordDocument (2026-11-12)

- HAR خروجی Firefox 158 شامل دو POST به سرویس محلی روی 127.0.0.1:1984 است: invoke=83011 بدون body ثبت‌شده و invoke=92123 با بدنه بزرگ.
- درخواست دوم دارای Content-Type برابر text/plain;charset=UTF-8 و Content-Length برابر 1391942 است و XML بیرونی آن متد EditWordDocument را dispatch می‌کند.
- پارامتر wordConfig شامل XML سند Base64 است. بخش قابل decode شده با word-document status="view" viewMode="protected" شروع می‌شود.
- مجوزهای نمونه view شامل غیرفعال بودن save/copy/print است. fieldهای امضا، شماره/تاریخ ثبت، نام امضاکننده، QR/barcode، گیرندگان و رونوشت‌ها دیده شدند؛ چند field تصویری با Base64 منتقل می‌شوند.
- HAR فقط 1,048,576 بایت از بدنه را نگه داشته، در حالی که Content-Length برابر 1,391,942 است؛ پس نمونه ناقص است. پاسخ هر دو درخواست محلی در HAR با status 0 ثبت شده و نتیجه واقعی پردازش از این فایل قابل تعیین نیست.
- این شاهد dispatch متد EditWordDocument و قالب لایه بیرونی/درونی را تقویت می‌کند، اما نمونه موجود حالت view/protected است و چرخه ویرایش/ذخیره را اثبات نمی‌کند.
- جزئیات ساختاری بدون محتوای نامه، تصاویر، کوکی‌ها یا tokenها در HTTP-LOCAL-API-ANALYSIS.md ثبت شد. فایل خام HAR به مخزن اضافه نشد.
- **گام بعد:** capture کامل و پاک‌سازی‌شده از یک نامه قابل ویرایش، سپس تغییر متن، بستن سند و مقایسه request/responseها برای کشف lifecycle ذخیره و بازگشت داده.


## Run 95 — مشاهده runtime پاسخ EditWordDocument هنگام بستن Word (2026-11-12)

- در Firefox، کاربر هنگام باز بودن نامه قابل ویرایش، یک POST به `127.0.0.1:1984` با `Content-Type: text/plain;charset=UTF-8` و query برابر `invoke=5208` مشاهده کرد.
- تغییر متن و فشردن `Ctrl+S` درخواست تازه‌ای به پورت 1984 ایجاد نکرد.
- هنگام بستن Word، POST به همان endpoint و با همان مقدار گزارش‌شده `invoke=5208` مشاهده شد؛ status برابر HTTP 200 بود و Response دارای XML بود.
- ابتدای Response شامل XML declaration، ریشه `<emwat version="1.0">`، متد `EditWordDocument` و پارامتر `wordConfig` بود.
- کاربر در ادامه XML، تگ‌های status/ErrorCode/Returntypes/Error را پیدا نکرد؛ محتوای کامل و ساختار پاسخ هنوز استخراج نشده است.
- **نتیجه محتاطانه:** چرخه بستن سند با یک پاسخ HTTP 200 از نوع XML همراه است. هنوز ثابت نشده که پاسخ حاوی متن ویرایش‌شده یا تأیید ذخیره نهایی در الماس گام است. HTTP 200 به‌تنهایی موفقیت ذخیره را اثبات نمی‌کند.
- مشاهده‌نشدن درخواست جدید هنگام ویرایش یا Ctrl+S فقط به همین نشست محدود است؛ timer/autosave یا مسیرهای دیگر هنوز بررسی نشده‌اند.
- جزئیات و محدودیت استنباط در [HTTP-LOCAL-API-ANALYSIS.md](HTTP-LOCAL-API-ANALYSIS.md) ثبت شد.
- **گام بعد:** مقایسه ساختاری Request و Response کامل `EditWordDocument` پس از حذف کامل اطلاعات نامه، تصاویر/امضاها، Cookie، Authorization و tokenها؛ سپس اتصال پاسخ runtime به مدل Wordresponsexml شامل Status، ErrorCode و Returntypes.


## Run 96 — decode ساختار XML سند قابل ویرایش (2026-11-12)

- کاربر مقدار کدشده `wordConfig` در Response مربوط به `EditWordDocument` را به‌صورت محلی decode کرد و XML داخلی را بررسی کرد.
- ریشه سند `word-document status="edit"` بود؛ permissionهای نمونه: چاپ غیرفعال، کپی فعال و ذخیره فعال.
- ساختار سطح بالا شامل `settings`، `fields`، `optional-attributes` و `requested-types` بود.
- `requested-types` مقدار `application/msword` داشت؛ این فقط MIME type اعلام‌شده است و قالب باینری واقعی خروجی را اثبات نمی‌کند.
- encodingهای مستقیم مشاهده‌شده در metadata فیلدها: CDATA ساده، `urlencoded` برای برخی فیلدهای متنی، و `base64` همراه `image/*` برای فیلدهای تصویری.
- خانواده‌های فیلد شامل metadata تولیدکننده/فرستنده، گیرندگان، امضاکنندگان با indexهای 0 تا 19، امضاها، QR و barcode است. وجود 20 slot به معنی پر بودن همه آن‌ها نیست.
- `optional-attributes` شامل `tokenizedReceivers` با type برابر `compInfo` مشاهده شد.
- نکته کلیدی: در همین XML decodeشده عنصر `<body>` وجود نداشت، در حالی که RTTI مدل request یک property به نام Body دارد. محل بدنه نامه و علت نبودن آن در این نمونه همچنان نامشخص است.
- XML ارسالی شامل مقادیر واقعی مکاتبه بود؛ فقط ساختار و نام فیلدها ثبت شدند و هیچ متن، نام، شناسه، تصویر، Base64 یا token در مخزن اضافه نشد.
- اسناد [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) و [HTTP-LOCAL-API-ANALYSIS.md](HTTP-LOCAL-API-ANALYSIS.md) با جزئیات پاک‌سازی‌شده به‌روزرسانی شدند.
- **گام بعد:** ردیابی در باینری برای مشخص‌کردن منبع Body در `LoadDocument/PrepareDocument` و ترتیب واقعی lifecycle بین autosave، BeforeClose و serialization پاسخ. تا پیش از اثبات، schema پاسخ و قالب فایل خروجی hard-code نمی‌شود.


## Run 97 — بازبینی انتساب نمادهای Word و تفکیک مسیر چاپ (2026-11-12)

- گزارش تجمیعی `EMWAT-Analysis-Results.txt` دوباره از روی مخزن بررسی شد؛ فایل مستقل `EmwatMethods.bpl1-strings.txt` در مسیر ریشه در پاسخ GitHub محتوای متنی برنگرداند، بنابراین تحلیل این مرحله بر خطوط تجمیع‌شده همان گزارش تکیه دارد.
- نماد `Emwatdocprinthandlerunit.TEmwatDocPrintHandler.FillField` و متدهای هم‌خانواده `PrepareDoc`، `Execute`، `CollectCustomField`، `GetDocFieldName` و تنظیم گیرندگان در کلاس PrintHandler قرار دارند. بنابراین `FillField` را نباید بدون شواهد بیشتر به مسیر اصلی بازکردن/ویرایش نامه نسبت داد.
- نمادهای مستقل `Wordviewer.OpenDoc`، `Wordviewer.TWordViwer.SilentSaveEmwatDoc`، `StoreFieldValuesForPrint` و `OnControlerNotify` وجود دارند. این‌ها وجود مرزهای جداگانه Word viewer و PrintHandler را تقویت می‌کنند، اما ترتیب اجرا یا caller/callee را اثبات نمی‌کنند.
- RTTI پراکنده برای `IXMLWorddocumentType.Get_Body`، `Get_Fields`، `Get_Status`، `Get_Permission`، `Get_Requestedtypes` و `Get_Optionalattributes` نیز در گزارش دیده می‌شود؛ این metadata ساختار مدل XML را تأیید می‌کند، نه اینکه Body در هر پیام runtime حاضر باشد.
- در این مرحله بدنه اجرایی متدهای `LoadDocument`، `PrepareDocument`، `SilentSaveEmwatDoc` یا eventهای BeforeClose استخراج نشد؛ بنابراین هیچ call graph یا ترتیب lifecycle جدیدی ادعا نمی‌شود.
- **گام بعد:** تهیه disassembly قابل اتکا از PE/BPL با mapping صحیح RVA/section و TD32 segment، سپس دنبال‌کردن entry pointهای Wordviewer و connector. تا آن زمان طراحی adapter بر اساس تفکیک مسئولیت‌های اثبات‌شده انجام می‌شود و FillField چاپ از مسیر ویرایش جدا می‌ماند.


## Run 98 — گسترش تحلیل ایستای چرخهٔ Word (2026-11-12)

- بررسی مجدد فایل تجمیعی `EMWAT-Analysis-Results.txt` نشان داد نام‌های قابل مشاهدهٔ Wordviewer در گزارش موجود محدودند؛ از جمله `Wordviewer.OpenDoc`، `TWordViwer.SilentSaveEmwatDoc`، `StoreFieldValuesForPrint`، `OnControlerNotify`، `TEDPController.Notify` و `TEditWordDocument.PerformMethod`.
- فایل گزارش تجمیعی، نام‌های صریحی برای `LoadDocument`، `PrepareDocument`، `OnTmrAutoSave` و eventهای BeforeClose/BeforeSave در بخش نمادهای قابل مشاهده نشان نداد. این به معنی نبودن متدها در باینری نیست؛ ممکن است RTTI-only، بدون نماد procedure یا خارج از این گزارش باشند.
- اسکریپت `disassemble_emwat_targets.py` برای probe کردن همین نام‌های تأییدشده و نام‌های موردنظر lifecycle گسترش یافت. خروجی همچنان فقط وقتی روش را disassemble می‌کند که TD32 procedure record و نگاشت PE معتبر وجود داشته باشد.
- اسکریپت `resolve_td32_helpers.py` نیز برای ساخت direct-call graph از متدهای Wordviewer/connector گسترش یافت؛ dispatchهای virtual/indirect همچنان unresolved می‌مانند و مسیر PrintHandler از مسیر ویرایش تفکیک شده است.
- اجرای workflow تحلیل BPL با commitهای `2c792c4` و `0eef619` آغاز شده است؛ تا زمان ثبت این Run نتیجهٔ نهایی و artifactها هنوز در دسترس نبودند. بنابراین هنوز هیچ آدرس، call graph یا ترتیب lifecycle جدیدی ادعا نمی‌شود.
- **گام بعد:** بررسی خروجی TD32 disassembly و helper graph پس از پایان workflow؛ اگر متدهای اصلی نماد/بازهٔ معتبر نداشته باشند، مسیر بعدی باید از RTTI/VMT و callerهای مستقیم `OpenDoc` و `SilentSaveEmwatDoc` ادامه پیدا کند، نه حدس‌زدن آدرس‌ها.


## Run 99 — بررسی artifact و تحلیل Wordviewer (2026-11-12)

- هر دو اجرای workflow مربوط به commitهای `2c792c4` و `0eef619` با نتیجه `success` تمام شدند؛ اجرای دارای آخرین تغییرات اسکریپت‌ها 145 مرحله را بدون failure گذراند.
- artifact با نام `emwat-bpl-static-analysis` دریافت شد؛ گزارش disassembly شامل 77 متد match‌شده است.
- mapping segment-relative برای متدهای Wordviewer در PE section `.text` با امتیاز plausibility حدود 85 تا 90 به دست آمد. entryهای `OpenDoc`، `LoadDocument`، `OnTmrAutoSave`، `PrepareDocument`، `BeforeClose`، `BeforeSave` و `SilentSaveEmwatDoc` اکنون قابل بررسی هستند.
- `OnTmrAutoSave` pointer یک handler را به آدرس دقیق `WordAppDocumentBeforeSave` ثبت می‌کند؛ این وجود اتصال timer/event به BeforeSave را نشان می‌دهد، نه اینکه به‌تنهایی ذخیره یا ارسال خودکار هر tick را ثابت کند.
- `WordAppDocumentBeforeSave` وضعیت سند را بررسی می‌کند و در branchهایی مقدار cancel را تنظیم می‌کند؛ رفتار Ctrl+S و ارسال به سامانه هنوز از این کد اثبات نشده است.
- `WordAppDocumentBeforeClose` به helper داخلی `0x004BCA88` می‌رسد، اما فراخوانی مستقیم قابل‌تشخیص به `SilentSaveEmwatDoc` در بدنه آن نیست.
- `SilentSaveEmwatDoc` بدنه اجرایی دارد: چند collection/property داخلی را می‌خواند، helper `0x004AEBBC` را اجرا می‌کند، flag داخلی را تنظیم می‌کند و virtual dispatch دارد. مقصد ذخیره و رابطه مستقیم آن با پاسخ HTTP هنوز نامعلوم است.
- مسیر `StoreFieldValuesForPrint` از طریق `Base64Decode` و helperهای focus/window به مسیر چاپ مربوط می‌ماند و به‌عنوان serializer عمومی نامه تفسیر نمی‌شود.
- جزئیات پاک‌سازی‌شده در [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) ثبت شد.
- **گام بعد:** disassemble کردن callbackهای ثبت‌شده در timer، helper مربوط به BeforeClose، و حل caller/VMT dispatchهای OpenDoc و SilentSaveEmwatDoc؛ سپس اتصال شواهد استاتیک به request/response runtime.


## Run 100 — caller scan و اصلاح برداشت از SilentSave (2026-11-12)

- workflow جدید با SHA `44718f0` با موفقیت تمام شد: 147/147 مرحله، بدون failure.
- artifact جدید بررسی شد؛ چهار callback ثبت‌شده در مسیر timer، helper مورد استفاده BeforeClose و direct callerهای چند متد Word استخراج شدند.
- **اصلاح Run 99:** متد `SilentSaveEmwatDoc` با وجود نامش، از روی بدنه فعلی به‌عنوان serializer/ذخیره‌کننده نامه قابل تأیید نیست. بدنه آن به `SetRegistryValue`، `TfrmWordPrintOption.SetLetterReceivers`، `TfrmWordPrintOption.FreePrinters` و `TWrapRecord.LineCount` متصل است. caller مستقیم دیده‌شده `TWordViwer.GetDocFieldName` است، نه BeforeClose/BeforeSave. نقش دقیق آن تا حل virtual dispatchها نامشخص می‌ماند.
- **اصلاح Run 99:** آدرس `0x004BCA88` صرفاً helper مخصوص BeforeClose نیست؛ از دو محل `GetCaptionItemFont` نیز فراخوانی می‌شود. نقش آن نامشخص است.
- برای `OpenDoc` direct CALL xref در procedureهای TD32 دیده نشد؛ callback/VMT و callerهای خارج از محدوده همچنان ممکن‌اند.
- برای `LoadDocument` یک caller مستقیم در `TScanDocument.PerformMethod` دیده شد؛ بنابراین نباید آن را فقط به مسیر بازشدن نامه متنی نسبت داد.
- callbackهای timer هنوز به‌علت virtual/interface dispatch مقصد نهایی روشنی ندارند.
- جزئیات و اصلاحات در [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) ثبت شد.
- **گام بعد:** disassembly متد `TWordViwer.GetDocFieldName` و callerهای آن، حل interface/VMT callbackها، و یافتن مسیر غیرمستقیم فراخوانی `OpenDoc`. هیچ پیاده‌سازی save-letter بر مبنای نام `SilentSaveEmwatDoc` انجام نشود.


### Run 101 — Word lifecycle уточнения (2026-11-12)

- GitHub Actions run `43217998439` завершился успешно; artifact скачан и проверен.
- Добавлены disassembly для `TWordViwer.GetDocFieldName` (`0x004BB81C`) и `TWordViwer.GetCaptionItemFont` (`0x004C19C0`).
- `GetDocFieldName` вызывает `SilentSaveEmwatDoc` по адресу `0x004BBA86`, но это не подтверждает, что тот сериализует или отправляет тело письма. Контекст вызова — процедура получения/обработки имени поля.
- `GetCaptionItemFont` связан с caption/font и ImageGear (`IG_ext_load/unload`); он тоже вызывает общий helper `0x004BCA88`. Поэтому этот helper не является специфичным только для BeforeClose.
- Прямое назначение `SilentSaveEmwatDoc` и helper `0x004BCA88` остаётся открытым. Схема HTTP/XML и runtime trace пока не дают подтверждённого полного цикла сохранения текста письма.
- Подробности и ограничения интерпретации внесены в `docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md`.


### Run 102 — Word XML field helpers (2026-11-12)

- Workflow `43219502021` завершился успешно: 147/147 шагов, без ошибок.
- Caller scan уточнил: `GetCaptionItemFont` вызывается из `AddImagesToDoc`; helper `0x004BCA88` имеет три прямых caller: два в `GetCaptionItemFont`, один в `WordAppDocumentBeforeClose`.
- Новый helper `0x004BC980` используется в `GetXmlFieldInfo`, `GetDocFieldIndex` и `FillImgFldsForPrint`; вероятная зона ответственности — работа с XML field metadata/lookup, но точный интерфейс пока не установлен.
- Для следующего цикла добавлены disassembly targets: `GetXmlFieldInfo`, `GetDocFieldIndex`, `AddImagesToDoc`, `FillImgFldsForPrint`.
- Протокол текста письма и фактическое сохранение пока не подтверждены; дальнейшая работа направлена на различение text-field и image-field путей.


### Run 103 — XML field lookup و مسیر تصاویر Word (2026-11-12)

- اجرای `43220472439` موفق شد: 147/147 مرحله، بدون failure؛ artifact شماره `13946301787` بررسی شد.
- overload کوچک `GetXmlFieldInfo` در `0x004BFC18` دو collection داخلی را برای resolve کردن نام/metadata فیلد جست‌وجو می‌کند و index/مشخصه‌های رکورد را خروجی می‌دهد.
- `AddImagesToDoc` در `0x004C0410` از interface مربوط به XML field داده می‌خواند و در مسیر شرطی `GetCaptionItemFont` را فراخوانی می‌کند؛ این مسیر به پردازش تصویر/caption مربوط است، نه اثبات ذخیره متن نامه.
- در artifact این اجرا بدنه مستقلی برای `GetDocFieldIndex` و `FillImgFldsForPrint` match نشد؛ جزئیات آن‌ها همچنان باز است.
- هنوز serializer متن Body یا سازوکار قطعی ذخیره نهایی در Almas Gam پیدا نشده است. جزئیات و محدودیت‌ها در `WORD-DOCUMENT-PROTOCOL-ANALYSIS.md` ثبت شده‌اند.


### تکمیل schema پاسخ Word از RTTI (2026-11-12)

- گزارش نمادهای پروژه interface IXMLResponseWordType را با propertyهای Status، ErrorCode و Returntypes نشان می‌دهد.
- IXMLReturntypesType دارای Type و IXMLBodyType دارای Encryption است.
- IXMLWorddocumentType getter مربوط به Body و propertyهای Fields، Status، Settings، Permission، Requestedtypes و Optionalattributes دارد.
- این شواهد وجود Body و مدل response را در schema تأیید می‌کند، اما مقداردهی Body، قالب واقعی Returntypes و نقطه serializer هنوز مشخص نیست. نبودن body در نمونه decodeشده کاربر فقط به همان نمونه محدود است.
- جزئیات در WORD-DOCUMENT-PROTOCOL-ANALYSIS.md ثبت شد؛ مرحله بعد اتصال این interfaceها به بدنه اجرایی TEditWordDocument.PerformMethod و ParamsToXML است.


### Run 103 — XML field lookup and image-field path

- CI run 43222525062 completed successfully (147/147 steps).
- GetXmlFieldInfo overload at 0x004BFC18 performs lookups against XML field collections at object offsets +0x68 and +0x6C, returning a matching index and associated string metadata. This is field metadata lookup, not body serialization.
- Another GetXmlFieldInfo overload is named at 0x004BCA88. This supersedes the earlier tentative generic-helper label for that address; callers from caption/image and close paths are consistent with shared XML-field lookup.
- AddImagesToDoc at 0x004C0410 delegates to GetCaptionItemFont for a field-processing branch. It does not by itself reveal the full image transfer or save protocol.
- TEmwatMethod.Invoke at 0x0046C82C traverses a dictionary/enumerator-like structure. ParamsToXML at 0x0046AD10 is only a jump thunk to 0x00401068, so its implementation still needs resolving.
- The analysis still has not found TEditWordDocument.PerformMethod or the document-body extraction/response serializer. Details and caveats are in WORD-DOCUMENT-PROTOCOL-ANALYSIS.md.


### بررسی مقصد ParamsToXML (2026-11-12)

- `ParamsToXML` در `0x0046AD10` فقط یک jump thunk به `0x00401068` است؛ آن آدرس نیز به‌صورت غیرمستقیم از IAT slot `0x0062EE24` پرش می‌کند. نام import نهایی هنوز استخراج نشده، بنابراین فعلاً نمی‌توان آن را serializer پاسخ XML دانست.
- commit افزودن trace به workflow با SHA `d4577ce` وجود دارد، اما اجرای CI متناظر در فهرست Actions مشاهده نشد. در نتیجه این مرحله هنوز artifact تأییدشده جدید ندارد.
- جزئیات و محدودیت نتیجه در [WORD-DOCUMENT-PROTOCOL-ANALYSIS.md](WORD-DOCUMENT-PROTOCOL-ANALYSIS.md) ثبت شد.
- **گام بعد:** resolve کردن import در IAT، caller scan برای `ParamsToXML` و `TEmwatMethod.Invoke`، و یافتن ماژول حاوی `TEditWordDocument.PerformMethod`.


### Run 104 — نتیجه تحلیل import و callerهای مستقیم (2026-11-12)

Workflow run `43226336477` با موفقیت کامل (148/148 مرحله) پایان یافت. در artifact، slot آدرس `0x0062EE24` به `rtl230.bpl!@System@@AbstractError$qqrv` resolve شد؛ این نتیجه هیچ پیوندی با serializer نامه ثابت نمی‌کند. برای `ParamsToXML` در `0x0046AD10` و `TEmwatMethod.Invoke` در `0x0046C82C` نیز direct CALL reference پیدا نشد. این اسکن فقط فراخوانی مستقیم داخل executable sectionهای همین PE را پوشش می‌دهد و dispatch غیرمستقیم یا callerهای خارج از ماژول را نمی‌بیند.

از آنجا که `ParamsToXML` یک thunk پنج‌بایتی به `0x00401068` است، workflow در commit `2b440ed3ebe1e6b3d1a144941cefe43a5cf70ad9` برای disassemble کردن مقصد thunk و جست‌وجوی callerهای مستقیم آن گسترش یافت. تا دریافت artifact بعدی، مسیر serialization هنوز حل نشده است.


### Run 105 — اصلاح انتساب ParamsToXML

Run `43232846364` با موفقیت کامل (148/148 مرحله) پایان یافت. رکورد TD32 برای `ParamsToXML` در `0x0046AD10` یک candidate پنج‌بایتی unresolved است که فقط به `0x00401068` jump می‌کند. مقصد، import thunk به slot `0x0062EE24` است و این slot به `rtl230.bpl!@System@@AbstractError$qqrv` resolve می‌شود. بنابراین این trace بدنه serializer را نشان نمی‌دهد و انتساب فعلی آدرس به implementation واقعی ParamsToXML قابل اتکا نیست؛ احتمال forwarding به package دیگر یا mapping/alias نامعتبر وجود دارد.

این نتیجه به معنی آن نیست که ParamsToXML واقعاً AbstractError را اجرا می‌کند. در حال حاضر نباید از آن درباره ساخت XML یا ذخیره نامه نتیجه‌گیری کرد. بررسی package/import metadata و BPLهای وابسته گام بعدی است. مسیر serialization/بازگشت سند همچنان حل‌نشده باقی می‌ماند.


### Run 105 — مسیر ParamsToXML به احتمال زیاد abstract dispatch است

تحلیل artifact نشان داد نماد TD32 با نام `@Emwatmethod@ParamsToXML...` فقط پنج بایت دارد و به یک import thunk برای `rtl230.bpl!@System@@AbstractError$qqrv` پرش می‌کند. این با stub متد abstract در Delphi سازگار است و احتمال می‌دهد implementation واقعی از طریق override/VMT یا package دیگری ارائه شود؛ اما هنوز override واقعی شناسایی نشده و این فرض باید با VMT تأیید شود. متد `GetXmlFieldInfo` در کلاس `TWordViwer` و آدرس `0x004BFC18` تابع جداگانه‌ای است و نباید با `ParamsToXML` یکی گرفته شود.

برای ادامه، ابزار inventory نمادهای TD32 و گسترش تحلیل VMT به کلاس‌های `TEmwatMethod` و `TEditWordDocument` اضافه شد. اجرای CI جدید در حال تولید گزارش‌های این دو مسیر است. تا تأیید override، پیاده‌سازی serializer و چرخه save/return همچنان نامشخص است.


## Runهای 27 تا 31 — زنجیرهٔ فیلد و nested helper (2026-11-14)

- Runهای lifecycle شمارهٔ 27، 28، 29 و 30 با موفقیت پایان یافتند؛ artifactهای آن‌ها بررسی شده‌اند. Run 31 برای trace ساختار فهرست/آرایه و callerهای بالادستی در حال اجراست.
- اصلاح مهم receiver: تابع `0x004CCBBC` با نماد TD32 `WordAppDocumentBeforeClose` در callsite تابع `FillImgFldsForPrint`، از طریق Delphi nested-procedure static link فراخوانی می‌شود. عبارت receiver آن یعنی `[[ebp+8]-0x0C]` به local تابع والد می‌رسد که مقدار ورودی ECX را نگه می‌دارد.
- اسکن direct CALLها یک caller برای `FillImgFldsForPrint` پیدا کرد: `TWordViwer.GetFieldIndexInList` در `0x004CB361`.
- بدنهٔ کامل `GetFieldIndexInList` در Run 30 نشان داد تابع ابتدا از `0x004CB638` یک pointer به فهرست/آرایه دریافت می‌کند، تعداد عناصر را می‌خواند و عناصر ۳۲بیتی را با stride چهار بایت پیمایش می‌کند. هر عنصر در ECX به `FillImgFldsForPrint` داده می‌شود.
- در `FillImgFldsForPrint` این pointer به‌عنوان receiver دارای vtable استفاده می‌شود و dispatchهای `+0x28) و `+0x38` دارد. این شواهد، interface-like بودن عناصر را اثبات می‌کنند، اما IID/type و نام متدهای این slotها هنوز مشخص نیست.
- تابع `0x004CCBBC` فعلاً به‌عنوان nested helper در مسیر پردازش فیلد فهرست‌بندی می‌شود؛ نام TD32 به‌تنهایی event registration یا close-time execution را اثبات نمی‌کند. هیچ ارتباط مستقیم اثبات‌شده‌ای از این بدنه به POST محلی، `invoke=5208` یا XML `EditWordDocument/wordConfig` پیدا نشده است.
- رفتار محصول در سطح کاربر قطعی است: بستن سند تغییرات را اعمال می‌کند، حتی اگر Save زده نشده باشد. سازوکار داخلی این رفتار همچنان موضوع تحلیل است.
- مستندات جزئی در `WORD-COM-INTERFACE-DISPATCH.md` و `PRODUCT-WORKFLOW-ANALYSIS.md` به‌روز شدند.
- **گام بعد:** Run 31 را بررسی کن؛ تابع سازندهٔ فهرست `0x004CB638)، callerهای `GetFieldIndexInList` و helperهای field lookup را تحلیل کن. سپس نوع interface و مسیر مستقل ثبت رویداد Close را پیدا کن.


### Run 31 — شناسایی نوع interface فهرست فیلدهای Word (2026-11-14)

- Run 31 با موفقیت پایان یافت و artifact آن بررسی شد.
- نماد TD32 تابع `0x004CB638` برابر `TWordViwer.FillPrintDocFields` است. امضای تابع ورودی `DelphiInterface<Wordxp._Document>` و خروجی `DynamicArray<DelphiInterface<Wordxp.Fields>>` را مشخص می‌کند.
- `GetFieldIndexInList` خروجی آرایه را پیمایش می‌کند و هر عنصر `Wordxp.Fields` را در ECX به `FillImgFldsForPrint` می‌دهد. از طریق static link همان receiver در دو dispatch داخلی تابع `0x004CCBBC` استفاده می‌شود.
- بنابراین نوع receiver برای dispatchهای `+0x28) و `+0x38) در این مسیر اکنون **به‌صورت ایستا و با امضای تایپ‌شده** `Wordxp.Fields` شناسایی شده است؛ دیگر نباید آن را فقط interface-like یا `_Document` توصیف کرد.
- caller مستقیم `GetFieldIndexInList` تابع `TWordViwer.BGPrintWithGamPrintOptions` در `0x004C6F3F` است؛ این موضوع مسیر بررسی‌شده را به پردازش فیلدها در مسیر print-options مرتبط می‌کند، نه اینکه event واقعی Close را اثبات کند.
- Workflow بعدی برای استخراج VMT/RTTI wrapperهای `TWordFields`، `TWordField` و `TWordDocument` و بررسی امضای interfaceهای Word گسترش یافت.
- **گام بعد:** نگاشت slotهای `Wordxp.Fields +0x28) و `+0x38) به نام متدهای wrapper، و جست‌وجوی مستقل registration واقعی close event و dispatcher درخواست `invoke=5208`.


### Run 33 — تطبیق IID و معنای slotهای Word Fields (2026-11-14)

- Run 33 با موفقیت پایان یافت؛ artifact شامل `Word-interface-tables.md` و disassembly کامل `BGPrintWithGamPrintOptions` بود.
- RTTI رابط‌های WordXP این GUIDها را تأیید کرد: `Fields=00020930-0000-0000-C000-000000000046`، `Field=0002092F-0000-0000-C000-000000000046`، `_Document=0002096B-0000-0000-C000-000000000046)، `Tables=0002094D-0000-0000-C000-000000000046`. دو IID نخست با مستندات Microsoft Word مطابقت دارند.
- روی receiver از نوع `Wordxp.Fields)، slot `+0x28) با الگوی getter تعداد و استفاده به‌عنوان loop bound، به‌احتمال بسیار زیاد `Count` است؛ slot `+0x38) با ورودی index و خروجی interface، به‌احتمال بسیار زیاد `Item(index)` است که `Wordxp.Field` می‌دهد. این نام‌گذاری‌ها inference با اطمینان بالا هستند، نه استخراج declaration کامل vtable.
- تنها caller مستقیم `GetFieldIndexInList` در procedureهای TD32، تابع `BGPrintWithGamPrintOptions` در `0x004C6F3F` است. بنابراین مسیر بررسی‌شده در یک مسیر print-options/field-processing استفاده می‌شود؛ registration واقعی close-event هنوز اثبات نشده است.
- اسکن VMT نام‌محور، VMT کلاس‌های `TWordFields` و `TWordField` را در همین BPL پیدا نکرد؛ این نتیجه عدم وجود interfaceها را رد نمی‌کند، چون خود RTTI interfaceها را تأیید کرده است.
- **گام بعد:** بررسی slotهای `Wordxp.Field` و `Wordxp.Range` در `FillPrintDocFields`، تکمیل inventory wrapper symbols و جست‌وجوی مستقل callback registration و dispatcher واقعی invoke/response.


### Run 34 — نمادهای typed برای Word Field و Image Field (2026-11-14)

- Inventory شماره 34 علاوه بر interface RTTI، چند تابع با امضای صریح `Wordxp.Field` و `Wordxp.Fields` را پیدا کرد:
  - `TWordDocument.Get_Fields` در ماژول `EmwatConsts`، segment 1، section offset برابر `0x2A55C).
  - `TWordViwer.FillField` با `Wordxp._Document`، نوع XML فیلد و `Wordxp.Field`.
  - `TWordViwer.FillImageField` با `Wordxp._Document` و `Wordxp.Field` و پارامترهای تصویر.
  - `TWordViwer.FillMSWFields` و `AddImagesToDoc` با `Wordxp.Fields`.
  - `TEmwatDocPrintHandler.FillField` با `Wordxp.Field`.
- VMT inventory کلاس‌هایی با نام `TWordFields`، `TWordField` و `TWordFieldCollection` پیدا نکرد؛ اما RTTI خود interfaceها و IIDهای آن‌ها را تأیید کرده است.
- Workflow به trace کامل این توابع typed و getter `TWordDocument.Get_Fields` گسترش یافت. در این مسیرها می‌توان slotهای مربوط به `Wordxp.Field` را از استفادهٔ واقعی و نه از حدس نام کلاس شناسایی کرد.
- **گام بعد:** بررسی artifact اجرای workflow 41/42، استخراج بدنهٔ کامل `Get_Fields)، `FillField`، `FillImageField`، `FillMSWFields` و `AddImagesToDoc)، و تطبیق dispatchها با Code/Result و سایر propertyهای `Wordxp.Field`.


### Run 41 — getter تایپ‌شدهٔ Fields و مسیر FillImageField (2026-11-14)

- Run 41 با موفقیت پایان یافت و trace کامل getter و helperهای تایپ‌شده استخراج شد.
- `Wordxp.TWordDocument.Get_Fields` در `0x0042B55C) پس از گرفتن interface از accessor `0x0042ABA0)، روی interface slot `+0x80) را فراخوانی می‌کند. این یک positive control تایپ‌شده برای getter به نام `Get_Fields` است.
- اسکن direct CALL برای `0x0042B55C) هیچ caller مستقیمی پیدا نکرد؛ بنابراین ممکن است این getter از VMT/property path استفاده شود یا در مسیرهای بررسی‌شده استفاده نشده باشد.
- **اصلاح مهم:** این getter با slot `+0x80) است؛ بنابراین dispatch جداگانهٔ `+0x12C) در `FillPrintDocFields` را نباید بدون شناسایی signature آن، `Get_Fields` نامید. آن فراخوانی چند آرگومان خروجی دارد و معنایش هنوز باز است.
- `TWordViwer.FillImageField` امضای تایپ‌شدهٔ `Wordxp._Document` و `Wordxp.Field` دارد و در بدنه از slotهای `+0x40)، `+0x38)، `+0x20) روی receiverهای interface استفاده می‌کند. نام متدهای این slotها هنوز مشخص نیست.
- `FillMSWFields` و `AddImagesToDoc` نیز trace شدند؛ اولی روی آرایه/فیلدهای داخلی و دومی از interface `Wordxp.Fields` برای افزودن تصویر به سند استفاده می‌کند.
- **گام بعد:** شناسایی IIDهای `Wordxp.Range` و `StoryRanges`، تطبیق slotهای `Wordxp.Field` در `FillImageField`، و بررسی نتایج caller scans برای این helperها.


### Run 43 — caller graph برای field/image helperها (2026-11-14)

- Run 43 با موفقیت پایان یافت.
- `FillImageField` دو caller مستقیم دارد که هر دو از `FillTextField` هستند (`0x004BC9CB` و `0x004BCA10)) و هر دو EBP والد را به‌عنوان static link می‌فرستند؛ پس image-field branch یک nested path در text-field processing است.
- `FillMSWFields` چهار caller مستقیم دارد: سه مورد از `GetDocFieldIndex` و یک مورد از `GetCaptionItemFont`.
- `AddImagesToDoc` فقط یک caller مستقیم در scan دارد: `GetDocFieldIndex` در `0x004C0A5D).
- `FillField` و `TWordDocument.Get_Fields` هیچ CALL مستقیم در procedureهای TD32-bounded ندارند؛ indirect/VMT/property paths همچنان ممکن‌اند.
- این caller graph، `GetDocFieldIndex` را در مرکز field processing قرار می‌دهد: آن routine روی مجموعهٔ Word حرکت می‌کند، `FillMSWFields` را برای موارد منتخب صدا می‌زند و در یک branch، `AddImagesToDoc` را اجرا می‌کند.
- **گام بعد:** trace کامل والد `FillTextField` در `0x004BC980)، بررسی callerهای `GetDocFieldIndex)، و تعیین slotهای `Wordxp.Field` در nested `FillImageField`.


### Run 44 — audit pointerهای ثبت callback در PE (2026-11-14)

- Run 44 با موفقیت پایان یافت؛ ابزار جدید `tools/scan_pe_pointer_refs.py` تمام raw sectionهای PE را برای آدرس‌های ۳۲بیتی callback جست‌وجو کرد.
- برای routine `0x004CCBBC` هیچ exact pointer referenceای در کل PE پیدا نشد.
- در مقابل، آدرس‌های callbackهای شناخته‌شده در کد `OnTmrAutoSave` دیده شدند: `0x004CD154) در `0x004B8CA8)، `0x004CD54C) در `0x004B8CBE)، `0x004CE030) در `0x004B8D0E) و `0x004B8E81)، و `0x004D00AC) در `0x004B8CF6) و `0x004B8E60).
- بدنهٔ `OnTmrAutoSave` انتساب این callbackها را به زوج فیلدهای event object تأیید می‌کند: BeforeSave در `+0x80/+0x84)، NewDocument در `+0x90/+0x94)، `0x004CD9C0) در `+0x98/+0x9C)، و BeforePrint در `+0x88/+0x8C) (با انتخاب `0x004CE030) یا `0x004D00AC)).
- این نتیجه، فرض ثبت ایستای `0x004CCBBC) به‌عنوان BeforeClose را در همین BPL بسیار نامحتمل می‌کند؛ اما computed/runtime registration یا package دیگر هنوز کاملاً رد نشده است. چون همین تابع از مسیر print/field فراخوانی مستقیم دارد، فعلاً آن را nested print/field helper طبقه‌بندی کن، نه callback قطعی Close.
- **گام بعد:** یافتن event/connector دیگری که POST مشاهده‌شده به `127.0.0.1:1984/?invoke=5208` را هنگام بستن سند ایجاد می‌کند؛ هم‌زمان بررسی RTTI برای `Range` و `StoryRanges` و slotهای Wordxp.Field ادامه یابد.


### Run 45 — RTTI مربوط به StoryRanges و FormFields (2026-11-14)

- Run 45 با موفقیت پایان یافت.
- سه interface جدید WordXP از RTTI استخراج شد: `StoryRanges` با IID `0002098C-0000-0000-C000-000000000046)، `FormFields` با IID `00020929-0000-0000-C000-000000000046)، و `FormField` با IID `00020928-0000-0000-C000-000000000046).
- اسکن هدفمند، TypeInfo برای `Range` یا `_Range` در همین BPL پیدا نکرد؛ این موضوع وجود object/interfaceهای Range را رد نمی‌کند، اما فعلاً مانع نام‌گذاری slotهای آن است.
- `StoryRanges` یک candidate معقول برای بررسی dispatch تایپ‌نشدهٔ `_Document +0x12C) در `FillPrintDocFields` است، اما هنوز هیچ wrapper یا خروجی IID آن را اثبات نکرده است. این slot را فعلاً StoryRanges ننام.
- وجود `FormFields/FormField` نشان می‌دهد کد علاوه بر Fields/Field عادی Word، مدل جداگانهٔ فرم‌فیلدها را هم import کرده است.
- **گام بعد:** بررسی symbol inventory جدید برای getter/consumerهای StoryRanges و FormFields؛ سپس بررسی callerها و signature تابع FillTextField و slotهای Wordxp.Field.


### Run 47 — زنجیرهٔ FillTextField و nested FillImageField (2026-11-14)

- Run 47 با موفقیت پایان یافت؛ بدنهٔ کامل `FillTextField` در `0x004BC980) و caller scans استخراج شد.
- `FillTextField` دو بار nested helper `FillImageField` را صدا می‌زند (`0x004BC9CB)، `0x004BCA10)) و هر دو بار EBP والد را به‌عنوان static link می‌فرستد.
- `FillTextField` نه caller مستقیم دارد: چهار call از `GetXmlFieldInfo)، سه call از `GetDocFieldIndex)، و دو call از `FillImgFldsForPrint`.
- `GetDocFieldIndex` یک caller مستقیم دارد: `GetDocFieldName` در `0x004BBB2B).
- زنجیرهٔ جدید: `GetDocFieldName → GetDocFieldIndex → FillTextField → FillImageField)، با ورودی‌های اضافی از `GetXmlFieldInfo` و `FillImgFldsForPrint`.
- این ساختار، پردازش محتوای فیلدها و تصاویر را توضیح می‌دهد و به‌خودی‌خود event بستن سند نیست.
- **گام بعد:** trace کامل `GetDocFieldName) و callerهایش برای مشخص‌کردن اینکه فیلدها از کدام XML/config path انتخاب می‌شوند.


### Run 49 — کشف close callback دوم در uSendLog (2026-11-14)

- Run 49 با موفقیت پایان یافت و symbol inventory نام‌های دارای close را استخراج کرد.
- یک routine دوم با نام `WordAppDocumentBeforeClose` پیدا شد: `uSendLog.TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` در `0x005EC580)، اندازه `0x12) بایت، با امضای شامل `TObject` و `Wordxp._Document`.
- همان فرم شامل `CloseWordApp` در `0x005EBDA8) و `FormClose` در `0x005EBF20) است.
- wrapperهای `TWordDocument.Close()` در `0x0042FEB0) و overloadها در `0x0042FF08)، `0x0042FF7C)، `0x0042FFF4) نیز در inventory پیدا شدند؛ `ClosePrintPreview` در `0x00433A84) و `CloseMyDoc` در `0x005E9174) هم ثبت شدند.
- این‌ها هنوز candidate هستند؛ handler مربوط به `TfrmShowAutoSaveFiles` ممکن است فقط برای UI فایل‌های autosave باشد و لزوماً close سند اصلی نیست.
- Workflow بعدی بدنه، callerها، immediate refs و raw pointer refs این handler و wrapperهای Close را استخراج می‌کند.
- **گام بعد:** تحلیل run 52 برای تعیین اینکه کدام close path واقعاً به Word document اصلی و POST محلی مرتبط است.


### Run 53 — GetDocFieldName و انتخاب فیلدهای Word (2026-11-14)

- Run 53 با موفقیت پایان یافت؛ بدنهٔ کامل `TWordViwer.GetDocFieldName` در `0x004BB81C` استخراج شد.
- این routine رابط سند فعلی را از viewer می‌گیرد، `FillPrintDocFields` را برای ساخت آرایهٔ `DynamicArray<Wordxp.Fields>` در فیلد داخلی `+0xA4` فراخوانی می‌کند، سپس نام فیلدهای تنظیم‌شده را پیمایش کرده و برای هرکدام `GetDocFieldIndex` را صدا می‌زند.
- نتیجهٔ Boolean هر lookup در state/flagهای viewer اعمال می‌شود. بنابراین `GetDocFieldName → GetDocFieldIndex` یک مسیر مشخص برای تطبیق نام فیلدهای config با فیلدهای واقعی Word است.
- اسکن direct CALL برای `GetDocFieldName` هیچ caller مستقیمی در procedureهای TD32-bounded پیدا نکرد؛ ورود از VMT/property/indirect path یا legacy code هنوز ممکن است.
- **گام بعد:** ادامهٔ بررسی close callback دوم `uSendLog` و wrapperهای `TWordDocument.Close`؛ همچنین تعیین entry path تابع `GetDocFieldName` و اتصال field config به invoke/response.


### Run 54–55 — callback مربوط به فرم autosave و wrapperهای Close (2026-11-14)

- Run 54 و 55 با موفقیت پایان یافتند.
- `uSendLog.TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` در `0x005EC580` فقط ۱۸ بایت است: مقدار word در `[ecx]` را با `0x2E` مقایسه می‌کند و در صورت تطبیق `CloseWordApp` را در `0x005EBDA8` صدا می‌زند.
- `CloseWordApp` دو caller مستقیم دارد: `btnShowFileClick` و همین callback. این تابع مجموعهٔ documentهای فرم autosave را پیمایش می‌کند و سپس یک متد در slot `+0x104` روی object application-like صدا می‌زند. نوع دقیق interface هنوز نیاز به نگاشت دارد.
- raw pointer scan برای `0x005EC580` دو occurrence در `.text` پیدا کرد (`0x005EB524` و `0x005EB607`)؛ resource scan فرم `TFRMSHOWAUTOSAVEFILES` در workflow بعدی برای اثبات event binding اجرا می‌شود.
- wrapperهای WordXP: `TWordDocument.Close()` بدون آرگومان slot `+0x4D4` را صدا می‌زند؛ overloadهای ۱، ۲ و ۳ `OleVariant` به‌ترتیب slot `+0x29C` را؛ `ClosePrintPreview` slot `+0x36C` را. caller مستقیم برای wrapper بدون آرگومان پیدا نشد.
- `WordCompareCommandUnit.CloseMyDoc` با وجود نامش slot `+0x2BC` را صدا می‌زند که از positive control قبلی به `_Document.PrintOutOld()` نگاشت شده است؛ این مسیر close واقعی نیست.
- **طبقه‌بندی فعلی:** handler دوم یک close-related event واقعی برای UI فایل‌های autosave است، اما هنوز callback اصلی نامه نیست. `0x004CCBBC` نیز helper داخلی مسیر print/field است. مسیر POST اصلی هنگام بستن نامه همچنان نامشخص است.


### Run 57 — resource فرم autosave و event wiring (2026-11-14)

- ابزار جدید `scan_named_pe_resource.py` با موفقیت resourceهای RCDATA را استخراج و رشته‌های آن‌ها را بررسی کرد.
- resource `TFRMSHOWAUTOSAVEFILES` (۱۱۴۹ بایت) شامل `OnClose=FormClose`، `OnCreate=FormCreate` و `OnShow=FormShow` و eventهای list/button است؛ رشته‌ای برای `WordAppDocumentBeforeClose` یا event component مربوط به Word در آن دیده نشد.
- resource `TFRMSENDLOG` نیز فقط eventهای UI فرم را نشان داد.
- بنابراین handler دوم `WordAppDocumentBeforeClose` به‌صورت آشکار در DFM فرم autosave ثبت نشده است. اگر به Word متصل می‌شود، احتمالاً اتصال در runtime در `FormCreate`، `btnShowFileClick` یا helper بازکردن preview انجام می‌شود؛ هنوز اثبات نشده.
- **گام بعد:** trace `FormCreate` و `btnShowFileClick` در `TfrmShowAutoSaveFiles` برای پیدا کردن ساخت Word.Application و اتصال event؛ سپس تعیین اینکه این مسیر صرفاً preview/autosave است یا به close نامهٔ اصلی ارتباط دارد.


### Run 58 — symbol inventory برای فرم‌ها و method dispatcher (2026-11-14)

- Inventory نام‌های lifecycle جدید را پیدا کرد: `TfrmShowAutoSaveFiles.FormCreate` در `0x005EC1A8`، `FormShow` در `0x005EC1B4` و `btnShowFileClick` در `0x005EB81C`.
- در ماژول `EmwatConnector`، `TfrmSendLog.FormCreate` در `0x005ECB88` (اندازه `0x3CC`) و `FormShow` در `0x005ECF54` پیدا شد؛ این فرم ممکن است به connector/log UI مربوط باشد و بدنهٔ FormCreate باید بررسی شود.
- `TEmwatMethod.Invoke` در `0x0046C82C` (اندازه `0x1B1`) و چند `PerformMethod` از connector classes پیدا شدند: `TCompareWordDocument` در `0x005EF8AC`، `TEditExcelWorkBook` در `0x005EF300` و `TShowSendLog` در `0x005EFE4C`.
- Workflow به trace بدنهٔ این فرم‌ها و dispatcher گسترش یافت تا مسیر `invoke=5208` و تولید پاسخ XML بهتر شناخته شود.


### Run 59 — تأیید cleanup مسیر فرم autosave

- `TfrmShowAutoSaveFiles.btnShowFileClick` فقط ۱۰ بایت است و تنها `CloseWordApp` را فراخوانی می‌کند و برمی‌گردد.
- دو caller مستقیم `CloseWordApp` دقیقاً همین دکمه و handler `WordAppDocumentBeforeClose` فرم autosave هستند.
- این pair یک مسیر cleanup برای preview/autosave است؛ در بدنهٔ traceشده سند اصلی، field pipeline یا local connector را فراخوانی نمی‌کند. بنابراین این close handler را از مسیر اصلی نامه جدا نگه می‌داریم.


### Run 60 — بررسی reachability wrapperهای Word Close

- Run 60 با موفقیت پایان یافت.
- برای چهار overload تابع `TWordDocument.Close` در آدرس‌های `0x0042FEB0`، `0x0042FF08`، `0x0042FF7C`، `0x0042FFF4` و نیز `ClosePrintPreview` در `0x00433A84` هیچ direct CALL در procedureهای TD32-bounded پیدا نشد.
- هر overload Close یک raw pointer occurrence در `.text` نزدیک metadata/VMT کلاس WordXP دارد، اما این occurrenceها callsite نیستند.
- در نتیجه این wrapperها ممکن است از طریق VMT/property قابل دسترسی باشند، ولی فعلاً مسیر اصلی close-time update محسوب نمی‌شوند.


### Run 62 — TEmwatMethod.Invoke و connector PerformMethodها (2026-11-14)

- Run 62 با موفقیت پایان یافت.
- `TEmwatMethod.Invoke` در `0x0046C82C`، با ورودی `TDictionary<AnsiString, TValue>`، پارامترهای dictionary را استخراج/پیمایش کرده و در `0x0046C921` از یک dispatch غیرمستقیم در slot `+0x68` استفاده می‌کند.
- این slot candidate فراخوانی پیاده‌سازی method است، چون چند connector class متدهای `PerformMethod(TDictionary<AnsiString, TValue>)` دارند؛ نوع receiver و slot declaration هنوز با VMT اثبات نشده است.
- تنها CALL مستقیم پیدا شده به `TEmwatMethod.Invoke` از `Finalization` در `0x0046CA67` است؛ بنابراین مسیر درخواست معمول احتمالاً indirect/VMT یا از ماژول دیگری وارد می‌شود.
- پیاده‌سازی‌های نمونه trace شدند: `TCompareWordDocument.PerformMethod` در `0x005EF8AC`، `TEditExcelWorkBook.PerformMethod` در `0x005EF300` و `TShowSendLog.PerformMethod` در `0x005EFE4C`.
- هنوز هیچ‌کدام از این شواهد، شناسهٔ `invoke=5208` یا تولید XML `EditWordDocument/wordConfig` را مشخص نمی‌کند.
- **گام بعد:** یافتن VMT مربوط به `TEmwatMethod`، mapping slot `+0x68`، و tracing parser/registry که request ID را به object متد وصل می‌کند.


### Run 64 — اسکن همهٔ RCDATA formها

- Run 64 با موفقیت پایان یافت و ۱۴ named RCDATA resource پیدا شد.
- فرم‌های دارای `OnClose` قابل مشاهده فقط image-tools، autosave-files و simple-image-editor هستند؛ همگی UI cleanup paths هستند. `TFRMWORDPRINTOPTION` رویداد close سند Word ندارد.
- در هیچ resource رشتهٔ `WordAppDocumentBeforeClose`، `OnDocumentBeforeClose` یا event property مربوط به WordApplication پیدا نشد.
- `PACKAGEINFO` واحدهای Word مانند `WordViewer`، `WordConfigRequestXML`، `WordRequestXML`، `WordResponseXML` و `WordProcessing` را همراه `EmwatConnector` و `uSendLog` فهرست می‌کند. فرم اصلی ویرایش Word به‌صورت RCDATA form مجزا وجود ندارد؛ `TWordViwer` یک code class در `ScanRequestXML` است.
- این نتیجه DFM binding را رد می‌کند، اما runtime COM connection-point یا browser-side close/request path هنوز ممکن است.


## Connector dispatcher investigation — run 62 and follow-up scans (2026-11-14)

### Statically confirmed in run 62

- `TEmwatMethod.Invoke` is a TD32-bounded routine at `0x0046C82C–0x0046C9DC` (433 bytes) in the `Base64` module.
- Its TD32 signature takes `TDictionary<AnsiString, TValue>`. The body reads and iterates dictionary data, extracts invocation values, and performs an indirect call through slot `+0x68` at `0x0046C921` on the interface/object held in local `[ebp-8]`.
- Concrete methods named `PerformMethod(TDictionary<AnsiString, TValue>)` are present:
  - `TCompareWordDocument.PerformMethod` at `0x005EF8AC`
  - `TEditExcelWorkBook.PerformMethod` at `0x005EF300`
  - `TShowSendLog.PerformMethod` at `0x005EFE4C`
- These are structural matches for a connector-method dispatch design, but **the slot +0x68 receiver type, VMT/interface mapping and association between any concrete implementation and invoke ID 5208 remain unproven**.
- The only direct TD32-bounded CALL to `TEmwatMethod.Invoke` found in run 62 is from `Finalization` at `0x0046CA67`. This does not reveal the ordinary request entry path; an indirect dispatch or another module may call it.
- The run-62 VMT scan did not recover a validated VMT candidate for `TEmwatMethod` or `TEditWordDocument`. This is a limitation of the current candidate scan, not proof that no such VMT or implementation exists.

### Workflow extension committed

The lifecycle workflow now additionally:
- scans object/interface field references at displacement `+0x68`;
- scans TD32 direct callers and immediate references for the three known concrete `PerformMethod` routines;
- scans exact raw PE pointer occurrences for `TEmwatMethod.Invoke` and those concrete methods.

The resulting evidence should distinguish ordinary CALL xrefs, code immediates, metadata pointers and actual candidate VMT entries. A raw pointer match alone is not proof of registration.

### Current next actions

1. Decode the TXMLMethodType +0xC8 attribute-name literal at 0x0044C6A4 (implementation 0x0044C62C, reached via thunk 0x0044BA59). The method-name string is passed to TXMLNode.SetAttribute; the service parser expects method@class, so confirm whether the literal is class. Then map TXMLEmwatType +0x54 serializer getter at VTable address 0x0044B8CC (thunk 0x0044B7A9), which returns the serialized XML string at callsite 0x0046C937. TXMLParamType parameter serialization is proven: +0xB0 sets attribute name and +0x68 calls TXMLNode.SetText.
2. Keep the second +0x68 call at 0x0046CBB7 separate; it uses a different local receiver in the shared base wrapper's exception/response path.
3. Continue tracing the service parser/registry only where necessary to establish how XML method classes are resolved. The browser's `invoke=5208` value is already proven to be a random per-request nonce, not a method ID; the server-generated `TEmwatInvokeParam.SessionId` is separate.
4. Link the registered Word BeforeClose callback at 0x004CD154 to the parent-page `postMessage` that initiates the next `EditWordDocument` request, then trace the Save/No-save branches to the final Almas Gam commit. Preserve the user's close-applies-changes observation as a hard requirement.



## Browser bridge random invoke value — correction (2026-11-14)

The `EmwatService.exe-strings.txt` dump contains the complete obfuscated JavaScript bridge. Deobfuscating the string array and reading the script shows:

- The bridge listens for `window.addEventListener("message", ...)`.
- For each received message it extracts `event.origin`, `event.source` and `event.data`.
- It creates `requestId = Math.floor(Math.random() * 99999)`.
- It POSTs `event.data` to `http://127.0.0.1:$V{myport}?invoke=` plus that random integer.
- When readyState reaches 4, it returns `responseText` to the source window via `postMessage(responseText, origin)`.

**This supersedes the earlier assumption that the observed value `invoke=5208` might be a stable method ID.** The embedded bridge generates it with `Math.floor(Math.random()*99999)` solely to vary the XHR URL (`?invoke=` + nonce). It is a per-request URL nonce/cache-buster, not a method ID or response-correlation token. The service checks the presence of the `invoke` key but does not copy its numeric value into `TEmwatInvokeParam.SessionId`; that field is generated independently server-side. The bridge sends `event.data` as the POST body and posts `responseText` back to the original `event.source` and `event.origin`. The actual operation is named in the XML body, e.g. `<method class="EditWordDocument">`.

The service string dump also contains `TEmwatInvokeParam`, `ParseMethod`, `Calling ParseMethod exception:`, `Emwat method called from`, and `Unable to call "invoke" method:`. This confirms parser/invoke-related code paths exist by string evidence, but does not reveal their implementation.

### Revised investigation sequence

1. Map the service-created method instance's VMT slot `+0x0C` to the exact BPL base-class method and follow it into the BPL connector dispatch.
2. Resolve the BPL `TEmwatMethod.Invoke` slot `+0x68` receiver and map the concrete class/VMT entry for `TEditWordDocument`.
3. Identify the request-info object at `[ARequestInfo+0xD4]` and its size/read methods to prove the HTTP body extraction.
4. Trace the server-generated `TEmwatInvokeParam.SessionId` through response/context handling; keep it distinct from the browser's random `invoke` query value.
5. Link the `EditWordDocument` method to `wordConfig` serialization, response transport, and the user-observed apply-on-close behavior.


## Original service executable recovered from installer (2026-11-14)

The project Library contained the original `EmwatInstaller.exe`. Its embedded CAB was extracted locally with libarchive, revealing `EmwatService.exe`, `EmwatAgent.exe`, and the full package set. The extracted BPL is byte-for-byte identical to `analysis-input/EmwatMethods.bpl1` in the repository (Git blob SHA-1 match), validating the current BPL analysis against the installer package.

New document: `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`.

Key additional facts:
- The extracted `EmwatService.exe` is a 679,936-byte PE32 executable. It imports Indy 23 packages and contains RTTI for `TIdHTTPServer`, `TIdHTTPRequestInfo`, and `TIdHTTPResponseInfo`, consistent with the loopback HTTP bridge.
- Its embedded JavaScript bridge is confirmed in the executable, with the per-message random `invoke` value and request/response `postMessage` flow.
- The service PE contains `TEmwatInvokeParam` RTTI: a 20-byte Delphi record with managed fields `System.string` at offset 0 and `System.AnsiString` at offset 8, and named fields `SessionId`, `bUnloadPkg`, `bResultSet`, `BufferIn`, `AResponseInfo`, and `AContext`.
- The same record is declared in BPL unit `Emwat.Sys`; `Wordviewer.OpenDoc` at `0x004B7430` has a `PEmwatInvokeParam` parameter. The service handler's record fields and dynamic class dispatch are now statically traced, and the record pointer is stored at offset `+0x04` of the instantiated connector object. The direct concrete-method-to-`Wordviewer.OpenDoc` call chain is still being resolved.

The service executable has no TD32 debug section. Continue with PE/RTTI/import/x86 analysis locally; do not claim full symbolic reconstruction. See the new service analysis document for hashes, offsets and evidence limits.



## Service XML dispatch and concrete Word method target (2026-11-14)

Lifecycle run 76 plus local disassembly of the extracted service executable establish the main request pipeline:

- `TMainForm.IdHTTPServerCommandGet` at `0x0047BF30) constructs the 20-byte `TEmwatInvokeParam` record.
- Internal `SessionId` is generated by the service with `System.Random(900000)+100000` and converted with `IntToStr`. It is separate from the browser's `invoke=<random>` query value; the handler checks the query parameter collection but does not copy its value into `SessionId`.
- The POST body is stored in `BufferIn`; `AResponseInfo` and `AContext` are copied into the record.
- XML parser helper `0x00470B38) reads the `method` element's `class` attribute and the `param name` values into a `TMethodInfo` object.
- Dispatcher `0x00470D00) prefixes `T` to the class name, resolves it with `System.Classes.GetClass`, creates the instance, and calls its VMT slot `+0x0C`.
- The common base routine at `0x0046C9E0) calls `TEmwatMethod.Invoke` (`0x0046C82C)) and then invokes the concrete class's VMT slot `+0x10`.

**Concrete Word-edit entry found:** `TEditWordDocument` VMT `0x005ED764), slot `+0x10 = 0x005EE82C`. This target has executable code even though no TD32 procedure record covers it. The method reads the `document` parameter and calls helper `0x004B7724`; the next trace will identify that helper and follow document opening/automation.

The VMT scanner was corrected to inspect Delphi class RTTI directly and to include small 12-byte connector classes. It now finds the full connector class family. Some TD32 procedure labels do not align with the VMT class whose slot points at that address; VMT slot targets are the authoritative dynamic-dispatch mapping, while symbol-name discrepancies remain explicitly unresolved.

New repeatable tool: `tools/trace_pe_range.py`, used by the lifecycle workflow to disassemble VMT-target code ranges even when TD32 procedure records are missing. The workflow now traces all connector VMT slot `+0x10` bodies and the `0x004B7724` helper.



## Service HTTP-to-BPL dispatch recovered (2026-11-14)

The original service PE was extracted from the Library installer and analyzed directly. The handler is identified by RTTI as `TMainForm.IdHTTPServerCommandGet` (entry `0x0047BF30`). It initializes a local `TEmwatInvokeParam` record and calls the shared dispatcher at `0x00470D00` (`CALL` at `0x0047C0C5`).

**Statically confirmed:**
- Request routes inspect the keys `invoke`, `init`, and `heartbeat` in the request parameter collection.
- `invoke` enters the XML method-dispatch path; `init` returns the embedded JavaScript bridge; `heartbeat` handles the Agent heartbeat.
- The record layout is `SessionId +0x00`, `bUnloadPkg +0x04`, `bResultSet +0x05`, `BufferIn +0x08`, `AResponseInfo +0x0C`, and `AContext +0x10`.
- The service generates `SessionId` with `Random(900000)+100000` followed by `IntToStr`; it is not the browser's `invoke=5208` value.
- The request-body source at `[ARequestInfo+0xD4]` is identified with high confidence as `TIdHTTPRequestInfo.PostStream`; the handler reads a size-like value and then calls virtual slot `+0x0C` with a buffer/length pair. The exact stream virtual method names/signatures remain unresolved. `[ARequestInfo+0xD0]` maps to `Params`, and `[ARequestInfo+0xDC]` to `RemoteIP`.
- The shared dispatcher parses the XML, reads `method@class`, prefixes the class name with `T`, resolves it with Delphi `GetClass`, creates the class instance, stores the request-record pointer at object offset `+0x04`, then calls virtual slot `+0x0C`.
- Three additional internal service routines call the same dispatcher with embedded XML (including `ShowEmwatSetting` and `ShowSendLog`).

Service-side virtual slot `+0x0C` is now mapped to shared BPL routine `0x0046C9E0`, which calls `TEmwatMethod.Invoke` (`0x0046C82C`) and then the subclass's VMT slot `+0x10`. XML `class="EditWordDocument"` resolves to `TEditWordDocument`; its slot `+0x10` target is `0x005EE82C`, which reads the `document` parameter and calls helper `0x004B7724`. The remaining work is to trace this concrete method/helper through document opening, response serialization/transport, and the upstream close event. Full evidence: `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md` and `docs/WORD-COM-INTERFACE-DISPATCH.md`.


### Correction to run-62 connector dictionary and call-path interpretation (run 76)

The run-62 generic signature was initially read as `TDictionary<AnsiString, TValue>`; this was incorrect. The BPL's concrete generic RTTI and the service's `TMethodInfo.Params` type establish `TDictionary<AnsiString, AnsiString>`. The XML parser's string values therefore flow into the connector methods as a string-to-string dictionary.

The run-62 statement that the only direct CALL to `TEmwatMethod.Invoke` came from `Finalization` was also incomplete. The routine at `0x0046C9E0` (TD32 label `Emwatmethod.Finalization`) is the shared `TEmwatMethod` virtual wrapper at VMT slot `+0x0C`. The service dispatcher invokes that slot; the wrapper calls `TEmwatMethod.Invoke` at `0x0046C82C`, then invokes the concrete class's VMT slot `+0x10`. Thus the apparent finalization call is part of the ordinary request dispatch path.

The corrected class-RTTI scan also found the previously missed small connector classes (instance size `0x0C`). Their VMT slot `+0x10` targets are documented in `WORD-COM-INTERFACE-DISPATCH.md`; for `TEditWordDocument`, the concrete target is `0x005EE82C`. TD32 procedure labels for some other targets differ from the VMT class mapping, so keep those names and target addresses separate until code behavior is reconciled.


## TEditWordDocument payload keys and response generation (run 77)

The concrete `TEditWordDocument` VMT slot `+0x10` target `0x005EE82C` reads four named dictionary parameters: `wordConfig`, `wordBody`, `letterImages`, and `signData`. It starts a worker thread, logs `CoInitializing thread`, and passes those values plus the `TEmwatInvokeParam*` request context and an output-string reference to helper `0x004B7724`.

After the helper returns, `TEditWordDocument` copies the output string to the base dispatcher's result string and sets `bUnloadPkg=true`. Correction from the complete `LoadDocument` body: on a non-empty result path, `TWordViwer.LoadDocument` itself assigns the output to `AResponseInfo.ContentText` (`AResponseInfo` at record `+0x0C`, ContentText at object `+0xBC`), calls imported `IdCustomHTTPServer.TIdHTTPResponseInfo.WriteContent` via thunk `0x0040448C` / IAT `0x0062F9C0`, then sets `bResultSet=true` at record `+0x05`. Therefore the generic service dispatcher skips its fallback response branch for this successful path; the fallback remains for methods that do not set `bResultSet` themselves.

This statically connects the runtime `EditWordDocument` XML request to the generic HTTP response path. The exact response XML and Word automation/commit behavior are now narrowed to helper `0x004B7724` and its downstream calls. Run 77 captures the helper's complete TD32 procedure and caller references.


## Main Word editor BeforeClose callback identified (2026-11-14)

The actual main-editor Word close event callback is now identified and registered:

- `TWordViwer.OnTmrAutoSave` (`0x004B8A84`) stores `0x004CD154` at event-record offset `+0x80`.
- BPL export-table mapping and body strings identify `0x004CD154` as `WordAppDocumentBeforeClose`.
- The body first calls `TWordViwer.RollBackOriginalOptions` (`0x004CB108`), checks `Document.Saved` through `_Document` slot `+0xD8` (typed wrapper `TWordDocument.Get_Saved` at `0x0042BD94`), logs `Document.OnBeforeClose Called.`, displays the Persian prompt `محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات هستيد؟`, and logs `Document.OnBeforeClose succeed.`.
- Cancel sets the event's Cancel word to `0xFFFF`; Yes initializes the first OleVariant argument to `-1`; No initializes it to `0`.
- It calls the active `Wordxp._Document` interface slot `+0x29C` with three OleVariant arguments. The exported three-argument `TWordDocument.Close` wrapper at `0x00430070` dispatches this slot.
- The other registered callbacks are `+0x90 → 0x004CD54C` (`WordAppDocumentBeforeSave`), `+0x98 → 0x004CD9C0` (export name `WordAppNewDocument`; code includes Activation/Quitword handling), and `+0x88 → 0x004D00AC` or `0x004CE030` (BeforePrint).

This corrects the earlier swapped callback labels. It also distinguishes three close-named routines:
- `0x004CD154`: actual registered main-editor BeforeClose callback.
- `0x004CCBBC`: TD32-labelled nested image-field/print helper, not registered.
- `0x005EC589`: separate autosave-preview form handler.

The callback body does not directly issue the localhost HTTP request. The embedded browser bridge is a generic `postMessage → XHR → postMessage` forwarder; it does not contain close-specific logic. The remaining task is to identify the parent-page message sent when the Word close callback completes, and trace the save/No-save branches to the final Almas Gam commit.


## Run 82 and focused Invoke receiver workflow (2026-11-14)

- Lifecycle run 82 completed successfully. It confirms the decoded static parameter literals used by the concrete Word connector: `wordConfig`, `wordBody`, `letterImages`, and `signData`. The new repeatable tool `tools/decode_pe_strings.py` reads Delphi ANSI/UTF-16LE strings from PE virtual addresses; its output records the Delphi refcount/length header where available.
- A focused workflow, `.github/workflows/analyze-invoke-enumerator.yml` (workflow display name: **Analyze EMWAT Invoke receiver**), was added so the generic Invoke/XML receiver trace can run independently of the much larger lifecycle analysis.
- Focused run 1 traced helper 0x0044C238 and proved its TD32 symbol is `Emwatxml.TXMLEmwatType.AfterConstruction`; the only direct caller is `TEmwatMethod.Invoke` at 0x0046C877, passing the address of local `[ebp-4]`.
- RTTI identifies `TXMLEmwatType` at VMT 0x0044B9AC, instance size 0x5C, with one implemented interface at object offset +0x50 and interface VTable 0x0044B878 (IID e7e941dd-cf1c-4856-9cec-8b6d2370c439).
- Focused run 3 shows the class VMT's +0x68 slot is null, so the unresolved +0x68 call cannot be made on a plain `TXMLEmwatType` class VMT. Its implemented interface has a valid +0x68 VTable entry (thunk 0x0044B7D1), which is only a candidate until the dataflow proves the local receiver is that interface pointer.
- The class VMT's +0x68 slot is null; bytes at class-relative +0xB0/+0xCC are not valid pointer slots. The actual +0xB0 call is through the `TXMLEmwatType` implemented-interface VTable at `0x0044B878`. `TXMLMethodType` and `TXMLParamType` are present in RTTI with interface offsets +0x70 and +0x50 respectively.
- The dictionary enumeration helpers `0x0046DE84` and `0x0046E324` are separate from the +0x68 receiver dispatch. The earlier hypothesis that local `[ebp-8]` itself was a `TDictionary.TPairEnumerator` is withdrawn: that class's VMT has only its own leading enumerator slots and +0x68 falls in metadata/data, not an executable class virtual slot.

**Evidence boundary:** this advances the type of the first receiver in the chain and narrows the likely XML class/interface family, but the exact types of `[ebp-0x1C]` and `[ebp-8]`, plus the method name at +0x68, remain unresolved. See [WORD-COM-INTERFACE-DISPATCH.md](WORD-COM-INTERFACE-DISPATCH.md).


## Invoke XML-interface receiver investigation (2026-11-14)

The focused receiver workflow has now narrowed the unresolved `TEmwatMethod.Invoke` indirect dispatch at `0x0046C921` beyond the earlier dictionary-enumerator hypothesis:

- `Invoke` accepts `TDictionary<AnsiString,AnsiString>` and stores its first receiver in local `[ebp-4]`. The only direct caller of helper `0x0044C238` is `Invoke` at `0x0046C877`; TD32 labels the helper `TXMLEmwatType.AfterConstruction`. Treat that symbol as a helper label until its full factory/dataflow is resolved.
- Class RTTI identifies `TXMLEmwatType` at VMT `0x0044B9AC`, instance size `0x5C`, implementing IID `e7e941dd-cf1c-4856-9cec-8b6d2370c439` at interface offset `0x50` with VTable `0x0044B878`.
- That interface's `+0xB0` slot is at `0x0044B928` and points to thunk `0x0044B709`; its `+0x68` slot points to thunk `0x0044B7D1`. This is an interface VTable dispatch, not a class-VMT `+0xB0` slot.
- The next `+0xCC` call at `0x0046C8E6` acts on the returned object `[ebp-0x1C]`, not the original `TXMLEmwatType` interface. `TXMLMethodType` is a separate class with IID `55d7b886-a428-4f24-8766-6af7ab8f792d`, interface offset `0x70`, and VTable `0x0044BBF8`; its `+0xCC` and `+0x68` slots point to thunks `0x0044BA61` and `0x0044BB51` respectively.
- `TXMLMethodType` remains a candidate for a returned XML interface, not a proven runtime type for either local. The exact type of `[ebp-0x1C]` and `[ebp-8]` remains unresolved until the interface thunk bodies and out-parameter dataflow are traced.

The implementation-body trace adds a major semantic step: `TXMLEmwatType` interface slot `+0xB0` resolves to `TXMLMethodType.AfterConstruction` (`0x0044C458`), which constructs the method-type interface returned into `[ebp-0x1C]`. The `TXMLMethodType` interface slot `+0xCC` resolves to `TXMLMethodType.Insert` (`0x0044C754`), which inserts a child at index `-1` and returns an interface into `[ebp-8]`. RTTI identifies `TXMLParamType` as the child-parameter class; its implemented interface VTable is `0x0044BF5C`, with candidate `+0xB0` slot pointer `0x0044BDF5` and `+0x68` slot pointer `0x0044BEB5`. `Invoke` then passes the two dictionary pair strings to the returned child's `+0xB0` and `+0x68` slots respectively. This strongly indicates that `Invoke` constructs XML parameter child nodes and assigns each key/value pair; the exact property names still await the TXMLParamType thunk traces.

The initial focused dictionary/enumerator workflow completed successfully (run `43570769839`). The XML interface VTable workflow completed successfully (run `43571030574`). Latest thunk-trace workflow: `43571171939`; artifact pending at the time of this update. Detailed address evidence is in `docs/WORD-COM-INTERFACE-DISPATCH.md` and the `emwat-invoke-receiver-analysis` workflow artifact.


## Invoke XML interface chain — focused runs 6–9 (2026-11-14)

- The first receiver chain is now mapped through interface implementations, not just numeric VTable slots:
  - [ebp-4] is a TXMLEmwatType interface; its +0xB0 thunk 0x0044B709 adjusts Self by -0x50 and jumps to 0x0044C458.
  - 0x0044C458 is TD32-labelled TXMLMethodType.AfterConstruction. It returns a TXMLMethodType interface into the output pointer supplied by TEmwatMethod.Invoke.
  - [ebp-1C] is therefore a TXMLMethodType interface; its +0xCC thunk 0x0044BA61 adjusts Self by -0x70 and jumps to 0x0044C754.
  - 0x0044C754 is TD32-labelled TXMLMethodType.Insert. It invokes its own VMT slot +0x20 with index -1, then returns the created child interface into the caller's output pointer [ebp-8].
  - RTTI identifies the child interface candidate as TXMLParamType (interface offset +0x50, VTable 0x0044BF5C). Its +0xB0 and +0x68 VTable entries are 0x0044BDF5 and 0x0044BEB5; the Invoke loop passes the first dictionary-pair string to +0xB0 and the second to +0x68.
- This strongly maps [ebp-8] to TXMLParamType. The two TXMLParamType interface thunks are now resolved: +0xB0 pointer `0x0044BDF5` adjusts Self by -0x50 and jumps to `0x0044C8E4`; +0x68 pointer `0x0044BEB5` adjusts Self by -0x50 and jumps to shared XML-interface body `0x0044B568`. The `+0x68` implementation is now confirmed as `xmlrtl230.bpl!TXMLNode.SetText`, so the second dictionary-pair string is the XML parameter node's text/value. The `+0xB0` implementation at `0x0044C8E4` passes the first string to helper `0x0044B4C0` with literal `0x0044C95C`; its imported target and literal are being decoded to identify the key attribute.
- The generic dictionary enumerator is now separated from the XML receiver: helpers 0x0046DE84 and 0x0046E324 produce/iterate pair data, while TXMLParamType receives the pair fields through its own interface methods.
- Detailed instruction traces and VTable evidence are in [WORD-COM-INTERFACE-DISPATCH.md](WORD-COM-INTERFACE-DISPATCH.md).


Run `43571520321` completed successfully and produced artifact `14104388028` with the TXMLParamType thunk mapping. Run `43571683744` is tracing the two resolved implementation bodies (`0x0044C8E4` and `0x0044B568`) to establish the exact field semantics. 

## Invoke XML parameter serialization — confirmed (2026-11-14)

Focused run 11 (`43571811038`, artifact `14105075475`) closes the key/value setter question. In `TEmwatMethod.Invoke`, each dictionary pair is materialized as a child XML parameter node:

- Pair key → XML attribute `name`: `0x0044C8E4` passes the key and constant `0x0044C95C` to `0x0044B4C0`; the latter is the `xmlrtl230.bpl!TXMLNode.SetAttribute(UnicodeString, OleVariant)` import thunk, and the constant decodes to `name`.
- Pair value → XML node text: interface thunk `0x0044BEB5` reaches `0x0044B568`, the `xmlrtl230.bpl!TXMLNode.SetText(UnicodeString)` import thunk.

This is statically confirmed parameter-node structure, not yet runtime-confirmed end-to-end request XML. Next: resolve the method object's `+0xC8` attribute literal (likely the method/class discriminator based on service parser schema, but do not assume until decoded), and map `TXMLEmwatType` interface slot `+0x54` to the actual XML serialization getter. Then compare complete request/response XML with runtime captures.

## Invoke XML method envelope and serializer — confirmed (2026-11-14)

Focused run 16 (`43573798242`, artifact `14105735885`) maps the XML serialization getter and method-name attribute:

- `TXMLEmwatType` interface slot `+0x54` points to thunk `0x0044B7A9`, which adjusts `Self` by `-0x50` and jumps to `0x0044B590`.
- `0x0044B590` is the IAT thunk for `xmlrtl230.bpl!TXMLNode.GetXML`; this is the getter used to serialize the constructed XML node tree into Invoke's output string.
- `TXMLMethodType` implementation `0x0044C62C` calls `TXMLNode.SetAttribute` with literal `class` and the incoming method name.
- `TXMLMethodType.AfterConstruction` (`0x0044C458`) passes literal `method` into the XML element setup path. It also calls helper `0x00401430` with constant pointer `0x0044C4FC`; the second constant's semantic role remains pending.
- `TXMLMethodType.Insert` appends each parameter child. Every child node receives `name=` dictionary key and text equal to dictionary value, as confirmed in focused run 11.

The proven structure is therefore a `method` element with `class=` method-name and parameter children with `name` attributes and text values; `TXMLNode.GetXML` returns the serialized XML string. This remains static-analysis evidence; complete document envelope/encoding and runtime request capture comparison are still open.

## Generic Invoke XML serialization — current confirmed state (2026-11-14)

Focused runs 11 and 16 close the previous XML dispatch questions: TXMLMethodType.AfterConstruction initializes a method element; its +0xC8 setter assigns the incoming method name to attribute class; each dictionary pair becomes a parameter child with key in name and value in text; and TXMLEmwatType +0x54 calls xmlrtl230.bpl!TXMLNode.GetXML to serialize the tree. The constructor additional constant 0x0044C4FC remains unresolved. Complete envelope/encoding and runtime HTTP comparison remain open. Detailed evidence: docs/WORD-COM-INTERFACE-DISPATCH.md and docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md.

## XML constructor follow-up — run 17

Focused run 17 (`43574768657`, artifact `14106455607`) confirms `0x0044B4D8` is `xmlrtl230.bpl!TXMLNode.GetChildNodes`, called by `TXMLMethodType.AfterConstruction` before the `method` element is inserted. The constructor's second argument constant `0x0044C4FC` is not a valid Delphi string. The call to `0x00401430` is an IAT thunk via slot `0x0062EC40`, but its import identity is not yet resolved. Run 18 now inspects that exact import slot and nearby bytes. Do not infer an extra XML attribute or node from this unresolved call.


## XML constructor import lookup — run 19

Focused run 19 (`43575191082`, artifact `14106206890`) confirms that `0x0062EC40` is located in `.idata` but does not match any parsed import descriptor entry. Its on-disk DWORD is `0x00231274`; the target is outside the BPL image and may be unresolved/relocated. Therefore the helper at `0x00401430` and the IID-like constant at `0x0044C4FC` remain semantically unresolved. Do not describe the helper as QueryInterface or claim an extra XML field. Run 20 directly traces `TXMLParamType.AfterConstruction` (VMT `+0x0C`, address `0x0044B4F8`) to recover the parameter element tag.
 

## XML parameter element constructor — run 20 correction

Run 20 (`43576636790`, artifact `14106479073`) shows that `TXMLParamType` VMT `+0x0C` (`0x0044B4F8`) is an import-style jump thunk through `0x006302B4`, not a TD32 constructor procedure; the slot's on-disk target `0x0024060C` is outside the BPL image. The parameter XML element tag remains unknown. A TD32 decorated-symbol indexer was added as `tools/find_td32_class_procedures.py`; the next run uses it to locate actual `TXMLParamType` and `TXMLMethodType` procedure addresses before tracing constructors.

## XML constructor comparison — run 22

Run 22 (`43578292246`, artifact `14106852706`) completed successfully. TD32 indexing found `TXMLParamType.AfterConstruction` at `0x00614EC8` only in the separate `WordRequestXML` module, not in the indexed `XmlResponse` class procedures. The WordRequestXML constructor calls `0x0044B4D8` (`xmlrtl230.bpl!TXMLNode.GetChildNodes`) and then the still-unresolved helper `0x00401430` with binary GUID-like constant `0x00614F2C`; that constant is not a readable Delphi string. The XmlResponse VMT parent pointers (`0x00630314` for TXMLParamType and `0x0063030C` for TXMLMethodType) point outside the BPL image, so their parent class identities are not established.

**No parameter tag was recovered.** Do not treat the WordRequestXML constructor as the XmlResponse constructor without evidence that the classes share the relevant construction path. The exact child element tag, full XML envelope, encoding and runtime wire representation remain unknown. The generic Invoke tree facts established in runs 11 and 16 remain confirmed: `method` element, `class` method-name attribute, parameter `name` key attribute, value as node text, serialized via `TXMLNode.GetXML`.

Next analysis: resolve external parent VMT/class references and trace how XmlResponse creates/initializes the parameter node returned by `TXMLMethodType.Insert`; then return to the parent-page close-time POST and response protocol. Do not spend another run repeating the TD32 symbol index unless new module inputs arrive.

## XmlResponse parameter insertion trace — run 23

Run 23 (`43579138098`, artifact `14107224578`) completed successfully. The XmlResponse `TXMLMethodType.Insert` implementation calls its child-node collection's virtual slot `+0x20` with index `-1`, then converts the returned node to the `TXMLParamType` interface using a GUID-like constant. It does not pass a literal child-element name. `TXMLParamType.Set_Name` operates on the wrapped node's name-related attribute path; it does not establish the element tag. The method constructor separately passes literal `method` to the child-node collection's `+0x10` method, confirming the method element.

The external parent VMT pointers and helper `0x00401430` remain unresolved; the latter is an indirect jump through a slot not matched to a parsed import descriptor. **Parameter child tag is still unknown.** The next useful target is the external XML node-list virtual method/class contract and then the parent-page close-time POST. No native Linux runtime behavior is claimed by this static-analysis result.

## XML node-list Add/Get_Param comparison — run 24 (2026-11-14)

Run 24 (`43579618380`, artifact `14106929511`) traced the paired `TXMLMethodType.Add` and `Get_Param` procedures in `XmlResponse` and `.EmwatMethods`.

- Both `Add` implementations follow the same pattern: obtain the wrapped node's child-node collection and invoke collection virtual slot `+0x10` with a string argument and an output interface. This matches the method-construction path that explicitly supplies `method`.
- Both `Insert` paths instead invoke child-collection virtual slot `+0x20` with index `-1`; no element-name string is supplied at this level. The parameter element tag must therefore be established deeper in the collection/node-list implementation or its class metadata.
- The paired `Get_Param` bodies in the two modules are structurally equivalent. The XmlResponse implementation uses the already decoded literal `class` as the attribute name and the incoming string as its value.
- The direct-call scan reports no direct immediate CALL xrefs for these interface methods; use is expected through virtual/interface dispatch.

**Boundary unchanged:** no parameter child tag, complete XML envelope, or exact wire serialization was recovered. Next target is the node-list implementation behind child collection virtual slots `+0x10` and `+0x20`; prioritize the page-side close-time `postMessage` sender and corresponding HTTP response path in parallel. Do not treat this static analysis as proof of native Linux runtime behavior.

## Close callback deep trace queued — 2026-11-14

The lifecycle workflow now has a follow-up step for the registered `WordAppDocumentBeforeClose` body and pointer/caller references, `RollBackOriginalOptions`, and the three-argument Word `Close` wrapper. Commit: `b88451617f3500f8ec64e239902533b21ab82a4d`. This is an analysis-only extension; no native runtime behavior is implemented by it. The run output must be reviewed before drawing conclusions.
 
## Correction — run 25 address/symbol verification (2026-11-14)

Run 25 (`43580008821`, artifact `14108665890`) exposed incorrect target labels in the preceding analysis step. The TD32 symbol at `0x004CD154` is `TWordViwer.WordAppDocumentBeforeSave`, not `WordAppDocumentBeforeClose`. The LoadDocument/OnTmrAutoSave registration code at `0x004B8C9C–0x004B8CCE` explicitly stores `0x004CD154` at callback field `+0x80`, `0x004CD54C` at `+0x90`, and `0x004CD9C0` at `+0x98`; the conditional callback at `+0x88` is `0x004D00AC` or `0x004CE030`. Thus `0x004CD154` is conclusively the registered BeforeSave callback. Do not call it a close callback.

The actual TD32 procedure named `TWordViwer.WordAppDocumentBeforeClose` begins at `0x004CCBBC`, but its only direct immediate caller found is `FillImgFldsForPrint` at `0x004CCF8F`; no registration reference was found in the scanned raw pointer data. Therefore its name alone does not prove that this procedure is the live Word application close-event handler.

A second address error: `0x00430070` is `TWordDocument.SaveAs2000`, not a Close wrapper. The actual `TWordDocument.Close` overload procedures are TD32-labeled at `0x0042FEB0`, `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`; the latter is the three-argument overload. A three-argument Close invocation in the callback body dispatches through document interface VMT slot `+0x29C`, but the exact runtime target for that interface dispatch must be established by matching the interface VMT and wrapper semantics, not by assigning `0x00430070`.

Run 25 itself completed successfully, but its added trace commands targeted the wrong symbols for a close-event investigation. Treat its other outputs as useful only where the TD32 labels and address semantics are independently verified. Next analysis must trace the actual Close overload(s), find the genuine callback registration (if present), and distinguish the BeforeSave callback from document-close lifecycle. No claim about the page-side POST is changed by this correction.


## Word lifecycle — corrected Close overload trace (run 26, 2026-11-14)

Run 26 (43584217243, artifact 14109926135) completed successfully with all 16 workflow steps passing. 0x004CD154 is the registered TWordViwer.WordAppDocumentBeforeSave callback at viewer field +0x80, not BeforeClose. The separate TD32-named WordAppDocumentBeforeClose is 0x004CCBBC; its only direct bounded caller found is FillImgFldsForPrint at 0x004CCF8F, and no raw-pointer registration reference was found. Do not claim it is the live close event without further evidence.

TWordDocument.Close overloads: no-arg 0x0042FEB0 dispatches through interface slot +0x4D4; one-arg 0x0042FF08, two-arg 0x0042FF7C, and three-arg 0x0042FFF4 dispatch through +0x29C. The registered BeforeSave callback calls PreparePrintDocument (0x004CB108), checks the Word Saved property through +0xD8, conditionally displays the changed-document prompt, sets Cancel to 0xFFFF on Cancel, and directly invokes interface slot +0x29C with three OleVariant arguments (the same dispatch slot used by the three-argument wrapper at 0x0042FFF4) for Yes/No. 0x00430070 is SaveAs2000, not Close.

Still unresolved: concrete runtime target behind +0x29C; any separate close-event registration; page-side postMessage and close-time POST response semantics. The user's observed close behavior (changes apply even without pressing Save) remains authoritative and is not contradicted by this static trace. No native Linux runtime implementation is claimed.
