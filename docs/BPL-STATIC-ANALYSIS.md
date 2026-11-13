# تحلیل ایستای EmwatMethods.bpl1

تاریخ: 2026-11-10  
منبع: `analysis-input/EmwatMethods.bpl1`  
اجرای تحلیل: GitHub Actions run `42826864211`  
Artifact: `emwat-bpl-static-analysis`

## اعتبارسنجی فایل و خروجی

- فایل ورودی: 11,106,148 بایت
- PE32 / x86؛ ماشین `0x014C`
- ImageBase: `0x00400000`
- EntryPoint RVA: `0x00225518`
- اسکریپت ساخت گزارش را با موفقیت به پایان رساند و گزارش 10,707 خطی تولید کرد.
- Artifact با موفقیت آپلود شد.

## شواهد مستقیم مرتبط با اسکن و ویرایش تصویر

### 1. لایه اسکن و مدیریت فایل تصویر: GEAR32PD

جدول Importها، توابع زیر را از `GEAR32PD.DLL` نشان می‌دهد:

- `IG_scan_pages` و `IG_scan_source_select`: انتخاب منبع و اسکن صفحات
- `IG_IP_crop`: برش
- `IG_IP_flip`: وارونه‌سازی
- `IG_IP_rotate_multiple_90`: چرخش مضرب ۹۰ درجه
- `IG_image_dimensions_get` و `IG_image_resolution_get/set`: ابعاد و وضوح تصویر
- `IG_page_count_get`: شمارش صفحات
- `IG_load_file`, `IG_save_file`, `IG_load_FD`, `IG_save_FD`: بارگذاری و ذخیره
- `IG_display_image`: نمایش تصویر
- `IG_image_is_valid`, `IG_error_get/clear/check`: اعتبارسنجی و مدیریت خطا

این شواهد نشان می‌دهند بخشی از مسیر اسکن/تصویر از کتابخانه GEAR استفاده می‌کند؛ اما به‌تنهایی ثابت نمی‌کنند هر فرمان UI دقیقاً به کدام تابع متصل است.

### 2. لایه ImageEn

Importهای `PKIECtrl23.bpl` شامل این APIها هستند:

- `TImageEnProc.Rotate`, `RotateAndCrop`, `CropSel`, `Flip`
- `TImageEnProc.SetUndoLimit`
- `TImageEnView.Fit`, `FitToWidth`, `FitToHeight`, `SetZoom`
- `TImageEnMView.AppendImage`, `InsertImage`, `DeleteSelectedImages`, `GetImageCount`, `SetImage`
- `TImageEnMIO.Acquire`, `LoadFromFileAuto`, `SaveToFile`, `SaveToFileTIFF`, `PrintImage`
- `TImageEnIO.SaveToFileJpeg` و `PreviewPrintImage`

در نتیجه دست‌کم دو مسیر فنی تصویر در BPL حاضرند: GEAR32PD برای عملیات scan/image و ImageEn برای نمایش/ویرایش/ورود و خروجی و چاپ. میزان هم‌پوشانی و اینکه کدام فرم از کدام مسیر استفاده می‌کند هنوز باید از بدنه توابع مشخص شود.

## شواهد RTTI/نام‌های متدهای داخلی

رشته‌ها و نام‌های متادیتای Delphi این نام‌ها را برای فرم ویرایشگر ساده نشان می‌دهند:

- کلاس: `TfrmSimpleImageEditor`
- handlerها: `doCommand`, `btnRegisterClick`, `pbImgViewerPaint`, `cmbPagesChange`, `chkForceSinglePageClick`, `rgImageTypeClick`
- فیلد/ویژگی‌ها: `CropRect`, `VisibleCropBox`
- کنترل‌ها: `btnRRotate`, `btnLRotate`, `btnCrop`, `btnVFlip`, `btnOriginalImage`, `btnRegister`, `rgImageType`, `chkForceSinglePage`

برای فرم پیش‌نمایش اسکن نیز این نام‌ها موجودند:

- کلاس: `TfrmGScanPreview`
- handlerها: `PaintBoxPaint`, `doCommand`, `uibtnRegisterClick`, `PaintBoxMouseDown`, `PaintBoxMouseMove`, `PaintBoxMouseUp`, `cmbPagesChange`, `BitBtnRegisterClick`
- متد/نام مرتبط با ذخیره: `SaveEditedImages`
- فیلدها: `CropRect`, `CropShowFlag`, `CropMousPos`

نام‌های دیگر شامل `IImageProcessor`, `TImageProcessor`, `ImageProcessing`, `ScanToFile`, `ImageType`, `SelectScanner`, `RotateLeft`, `RotateRight`, `FlipHorizontal`, `FlipVertical`, `ReloadPage`, `FinalForceSinglePage`, `PageCount`, `PageNo`, `ResultImage` و `ShowImageEditor` هستند. این‌ها سرنخ‌های قوی برای مرزبندی ماژول‌ها و قرارداد workflow اسکن هستند، نه اثبات ترتیب فراخوانی یا معنای دقیق پارامترها.

## نتیجه مهندسی برای نسخه Linux

1. عملیات اصلی لازم برای ویرایش تصویر شامل rotate، crop، flip، reload/original، page navigation، نمایش/paint و export است.
2. workflow اسکن باید چندصفحه‌ای باشد و مفاهیمی مثل `PageCount`, `PageNo`, `FinalForceSinglePage` و `ResultImage` را مدل کند.
3. فرمت‌های TIFF و JPEG در لایه I/O شواهد مستقیم دارند.
4. APIهای ImageEn و GEAR32PD نباید به‌عنوان وابستگی مستقیم نسخه Linux فرض شوند؛ بهتر است یک abstraction مستقل برای ImageDocument، Page و ImageOperations تعریف شود و پیاده‌سازی Linux با کتابخانه بومی جایگزین شود.
5. منطق چاپ و Acquire اسکن باید جدا از هسته ویرایش تصویر طراحی شود.

## محدودیت این مرحله

اسکریپت فعلی PE headers، import table و رشته‌های مرتبط را استخراج کرده است. جستجوی اولیه ارجاع مستقیم به رشته‌ها `0` مورد گزارش کرده؛ این نتیجه به معنی نبود ارجاع یا نبود بدنه کد نیست، زیرا کد Delphi می‌تواند از طریق RTTI، relocation، جدول متدها و الگوهای فراخوانی غیرمستقیم به متدها برسد. این اسکریپت هنوز decompiler یا disassembler کامل برای استخراج بدنه `doCommand` و handlerها نیست.

**گام بعدی:** تحلیل Delphi RTTI/VMT و اطلاعات debug داخل بخش `.debug`، سپس disassembly هدفمند توابع handler. تنها پس از آن می‌توان Tagهای 11 تا 16 و قرارداد دقیق ورودی/خروجی را با اطمینان مستند کرد.


## Run 106 — تحلیل متمرکز چرخه عمر سند Word (2026-11-13)

برای جلوگیری از محدودیت traceهای 120 دستور قبلی، workflow مستقل `.github/workflows/analyze-word-lifecycle.yml` اضافه شد. این workflow روی commit `17bc0b4cb059b98a215622f6ae92639d2193dc53` اجرا شده و در زمان ثبت این یادداشت در وضعیت `in_progress` با run ID برابر `43499543674` قرار دارد.

### دامنه بررسی جدید

- گسترش disassembly callbackهای `0x004CD9C0`، `0x004CE030`، `0x004D00AC`، `0x004CCBBC` و `0x004CD154` تا 320 دستور یا انتهای تابع.
- trace مستقل helper در `0x0044ABE4`.
- dump داده و رشته‌های اطراف ثابت‌های استفاده‌شده در callbackها در آدرس‌های `0x004CDAA0`، `0x004CDAB8`، `0x004CDAE4`، `0x004CDAF4`، `0x004CEB44`، `0x004CEB84`، `0x004D0550`، `0x004D0590` و `0x004D05A8`.

### وضعیت شواهد پیش از دریافت artifact جدید

- کاربر تأیید کرده است که تغییرات سند با بستن سند در سامانه Almas Gam اعمال می‌شوند؛ این رفتار عملیاتیِ تأییدشده است.
- callback در `0x004CD9C0` سه مقدار رشته‌ای محلی می‌سازد و آن‌ها را همراه شیء `ebx` به dispatch مجازی در VMT offset `+0x29C` می‌دهد. مالک VMT و اثر واقعی متد هنوز مشخص نیست.
- callbackهای `0x004CE030` و `0x004D00AC` از reference در offset `+0x48`، خواندن property با شناسه `0x61` از شیء `+0x44` و dispatchهای interface از شیء `+0x40` استفاده می‌کنند. معنای property و مقصد نهایی dispatchها هنوز اثبات نشده است.
- این شواهد هنوز مسیر استخراج محتوای Word، ساخت payload و ارسال آن به Agent/Service یا Almas Gam را نشان نمی‌دهند. نباید از نام callbackها یا وجود dispatch مجازی، انتقال شبکه‌ای را نتیجه گرفت.

### گام بعدی

پس از پایان run، traceهای کامل و داده‌های ثابت‌ها بررسی می‌شوند. سپس dispatch مربوط به `+0x29C` از طریق RTTI/VMT و محل ساخت شیء پیگیری خواهد شد. نتیجه run و هر اصلاح در تفسیر callbackها باید در همین سند و سند پروتکل Word ثبت شود.


### اصلاح ابزار تحلیل پس از Run 106

بازبینی artifact اجرای اول نشان داد که با وجود آرگومان 320 دستور، ابزار `trace_pe_target.py` در عمل ورودی disassembler را به 256 بایت محدود می‌کرد. بنابراین traceهای callbackهای طولانی در انتهای همان بازه متوقف شده بودند؛ موفقیت CI فقط موفقیت اجرای اسکریپت بود و به معنی کامل بودن traceها نبود.

این نقص در commit `357e089e17fd4075d25b4c906d4d53ad6759f8d4` اصلاح شد: اندازه بافر disassembly اکنون بر اساس سقف دستور درخواستی (حداکثر 15 بایت برای هر دستور x86) و انتهای واقعی داده بخش PE محاسبه می‌شود. اجرای مجدد workflow با run ID `43499689891` در حال انجام است. نتایج artifact اول فقط برای شواهدی که داخل 256 بایت ابتدایی آن قرار دارند معتبرند؛ برای ادامه تحلیل باید از artifact اجرای اصلاح‌شده استفاده شود.

در داده ثابت‌های callbackها، رشته UTF-16 در `0x004CEB44` و `0x004D0550` برابر **`Document.OnBeforePrint called.`** خوانده می‌شود. این قرینه نشان می‌دهد callbackهای `0x004CE030` و `0x004D00AC` دست‌کم به مسیر event مربوط به BeforePrint متصل‌اند؛ اما هنوز معلوم نیست این event در چه شرایطی نسبت به بستن سند اجرا می‌شود یا چه نقشی در ثبت تغییرات دارد. این رشته به‌تنهایی اثبات ارسال سند یا payload نیست.


### نتیجه artifact اصلاح‌شده — Run 106

اجرای اصلاح‌شده `43499689891` با موفقیت پایان یافت و artifact شماره `14073900603` تولید شد. پس از رفع محدودیت 256 بایتی، traceهای کامل‌تر نشان دادند:

- `0x004CE030` تا `0x004CE369` ادامه دارد و به‌وضوح یک مسیر BeforePrint پیچیده است.
- `0x004D00AC` تا `0x004D03D2` ادامه دارد و مسیر موازی دیگری با ساخت/مدیریت context چاپ و چند helper داخلی را اجرا می‌کند.
- هر دو مسیر ابتدا پیام `Document.OnBeforePrint called.` را از طریق logger سراسری `0x0062B3A0` ثبت می‌کنند.
- مسیر `0x004CE030` داده‌های چند فیلد/مجموعه در offsets `+0x90`، `+0x94`، `+0x98` و `+0x9C` را می‌خواند و در انتها helper `0x004AEBBC` را با دو interface و context چاپ فراخوانی می‌کند.
- مسیر `0x004D00AC` از dispatchهای مجازی `+0xF0`، `+0x84` و `+0x40` استفاده می‌کند و helperهای `0x004CF5B4`، `0x004CF748`، `0x004CFC74`، `0x004CF158` و `0x00441E44` را در مسیر ساخت و پاک‌سازی context صدا می‌زند.
- callback واقعی `WordAppDocumentBeforeClose` در `0x004CCBBC` جداست و مسیر metadata/field lookup را از طریق `GetXmlFieldInfo` در `0x004BCA88` انجام می‌دهد.

این نتایج نشان می‌دهند callbackهای فوق مسیر چاپ‌اند و نباید به‌عنوان مسیر ثبت تغییرات هنگام بستن سند تفسیر شوند. رفتار کاربر مبنی بر اعمال تغییرات با بستن سند همچنان تأییدشده است، اما سازوکار انتقال/ثبت آن هنوز پیدا نشده است.

در commit `3c4c5b577911b1e2beed49ceee7ac8a9cc6bf540`، trace helperهای downstream و رشته‌های پیام این دو callback به workflow افزوده شد. اجرای جدید باید این helperها را روشن کند؛ سپس تمرکز اصلی به dispatchهای غیرمستقیم و VMT متصل به `WordAppDocumentBeforeClose` و شیء Word document بازمی‌گردد.


### بررسی تکمیلی Run 106: تفکیک دقیق مسیر چاپ و رشته‌های callback

در artifact اصلاح‌شده `14072584235` (run `43499889762`) trace helperهای چاپ بررسی شد:

- `0x004CF5B4` دو مجموعه از مقادیر را از ساختار context می‌خواند و به دو interface می‌دهد؛ سپس `0x004AEBBC` را با context سراسری فراخوانی می‌کند.
- `0x004AEBBC` مقادیر را به چند interface/کنترل مرتبط با context منتقل می‌کند و متدهای مجازی روی آن‌ها اجرا می‌کند.
- `0x004CF748` propertyهای متعدد از context چاپ را بررسی و به اشیای مقصد منتقل می‌کند.
- `0x004CFC74` propertyهای بیشتری را از اشیای global/context جمع‌آوری می‌کند.
- `0x004CF158` وضعیت‌ها و مجموعه‌های دیگری از context چاپ را پیمایش می‌کند.
- `0x00441E44` یک متد مجازی با offset `+0x1E4` روی یک interface اجرا می‌کند؛ نام و اثر متد هنوز مشخص نیست.

این الگوها با آماده‌سازی و انتقال metadata بین اجزای داخلی print context سازگارند؛ اما بدون نام‌گذاری RTTI مقصدها، نباید معنای دقیق هر property یا خروجی چاپ را قطعی اعلام کرد.

در تابع `0x004CD9C0`، سه مقدار رشته‌ای محلی ساخته و به متد مجازی `+0x29C` ارسال می‌شود. داده UTF-16 اطراف این تابع شامل متن فارسی **«دسترسی به این بخش میسر نیست»** و عبارت **«اموتا - Gam Document»** است. این شواهد احتمالاً به پیام/بررسی دسترسی مربوط‌اند؛ اما هنوز ثابت نمی‌کنند این callback بخشی از ثبت یا انتقال سند است. مالک VMT و قرارداد پارامترها باید مشخص شود.

### Run 107 — تمرکز بر lifecycle واقعی بستن سند

Workflow در commit `7f85037a9f2f31f529128ffd29f3679acb41f840` گسترش یافت تا بدنه این نقاط را نیز trace کند: `GetXmlFieldInfo (0x004BCA88)`، `OnTmrAutoSave (0x004B8A84)`، `OnControlerNotify (0x004BB3B0)`، `OpenDoc (0x004B7430)` و `LoadDocument (0x004B7724)`.

این انتخاب بر اساس مشاهده runtime قبلی است: هنگام بستن سند، مرورگر POST به `127.0.0.1:1984` با `invoke=5208` می‌فرستد و ابتدای پاسخ XML شامل `EditWordDocument` و پارامتر `wordConfig` است. در disassembly فعلی، `WordAppDocumentBeforeClose (0x004CCBBC)` مستقیماً `GetXmlFieldInfo` را صدا می‌زند؛ اما هنوز caller/dispatcherی که POST را تولید می‌کند و ترتیب ارتباطش با BeforeClose مشخص نشده است.

**هدف این مرحله:** اتصال runtime مشاهده‌شده `EditWordDocument` به مسیرهای `OpenDoc`، `OnControlerNotify`، `OnTmrAutoSave` و event بستن، بدون فرض گرفتن اینکه یکی از آن‌ها به‌تنهایی مسئول ارسال است.


### نتیجه Run 107 — اتصال callbackها و controller (2026-11-13)

Artifact شماره `14073059427` از run `43500269235` بررسی شد.

**یافته قطعی درباره ثبت callbackها در `OnTmrAutoSave`:**

در `0x004B8A84`، کد یک شیء وابسته به Word را از فیلد `+0x44` دریافت می‌کند و callback pointerها را در ساختار آن تنظیم می‌کند:

- offset `+0x80` ← `WordAppDocumentBeforeSave` در `0x004CD154`
- offset `+0x90` ← callback در `0x004CD54C`
- offset `+0x98` ← callback در `0x004CD9C0`
- offset `+0x88` ← یکی از دو callback چاپ، `0x004D00AC` یا `0x004CE030`، بر اساس byte در `[this+0x3C]`

این مشاهده ثابت می‌کند `OnTmrAutoSave` حداقل بخشی از wiring رویدادهای Word را انجام می‌دهد. نام متد به‌تنهایی نباید باعث شود تمام بدنه آن را «ذخیره خودکار» فرض کنیم؛ در trace موجود، ثبت callbackها و آماده‌سازی handlerها مستقیماً دیده می‌شود.

**رفتار `OnControlerNotify` در `0x004BB3B0`:**

- ابتدا property/وضعیتی از شیء `+0x7C` خوانده می‌شود.
- در صورت برقرار بودن شرط روی `[this+0x58]`، داده‌ای از شیء `+0x44` از طریق helper `0x43EB70` گرفته و متد interface با offset `+0xE0` اجرا می‌شود.
- سپس دو مقدار/وضعیت دیگر از همان interface خوانده می‌شوند و مقدار اول با حد `0x14` مقایسه می‌شود.
- در مسیر اصلی، byteهای `+0x79` و `+0x5E` موقتاً تغییر می‌کنند، helper `0x004D281C` اجرا می‌شود و سپس متد interface با offset `+0xDC` روی شیء `+0x48` فراخوانی می‌شود.
- در trace محدود فعلی، HTTP، XML serialization یا ارسال مستقیم به endpoint دیده نمی‌شود.

**رفتار فعلی `GetXmlFieldInfo` در `0x004BCA88`:**

تابع stack frame بزرگی می‌سازد، چند interface را از ورودی دریافت می‌کند، propertyهای متعدد را با dispatchهای interface (offsetهای `+0x70`، `+0x40`، `+0x38`، `+0x30`، `+0x28`، `+0x88`) می‌خواند و وارد پیمایش مجموعه‌ای از فیلدها می‌شود. helper `0x004BC170` و مقایسه رشته/مقدار نیز در این مسیر دیده می‌شوند. این با استخراج و تطبیق اطلاعات فیلدهای XML سازگار است، نه ارسال شبکه‌ای مستقیم. trace فعلی 320 دستور است و هنوز انتهای کامل تابع را پوشش نمی‌دهد.

### Run 108 — گسترش trace کامل

در commit `b17be55941a861a19348ca8fd70cfb8514a9225e`، workflow برای trace عمیق‌تر `OnTmrAutoSave` تا 2600 دستور و `GetXmlFieldInfo` تا 1800 دستور، به‌علاوه helperهای `0x004D281C`، `0x004CDB54`، `0x004C5D68`، `0x00440950`، `0x00440A68` و `0x00441C68` توسعه یافت. هدف مشخص‌کردن ترتیب ثبت callbackها، نقش controller و هرگونه مسیر رسیدن به connector است.
