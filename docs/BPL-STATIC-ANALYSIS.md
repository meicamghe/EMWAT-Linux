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
