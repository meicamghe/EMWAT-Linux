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
