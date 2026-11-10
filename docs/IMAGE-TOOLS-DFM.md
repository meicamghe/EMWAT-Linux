# تحلیل فرم ابزارهای تصویر (TfrmImageTools)

تاریخ: 2026-11-10  
منبع: `analysis-input/RCDATA_TFRMIMAGETOOLS_14.bin` از `EmwatMethods.bpl1`  
روش: decode مستقیم Binary DFM با امضای `TPF0`؛ هیچ فایل اجرایی اجرا نشده است.

## اعتبارسنجی
- اندازه فایل: 57,832 بایت
- امضا: `TPF0`
- parser تمام 57,832 بایت را مصرف کرد؛ 0 بایت باقی‌مانده
- فرم ریشه: `TfrmImageTools` / نمونه `frmImageTools`
- عنوان: «ويرايش تصوير» (ویرایش تصویر)
- ClientWidth=792، ClientHeight=578؛ پنجره در حالت Maximized
- BiDiMode برابر `bdRightToLeft`
- رویدادهای فرم: `FormCreate`، `FormShow`، `FormActivate`، `FormClose`

## معماری UI

### 1. نمای چندصفحه‌ای و انتخاب تصویر
- `iemvImageHolder` از نوع `TImageEnMView` داخل پنل سمت چپ قرار دارد و Hint آن «نمایش کلی صفحات» است.
- رویدادهای آن شامل `OnImageSelect`، `OnImageDeselect`، `OnBeforeImageDraw`، DragDrop/DragOver/EndDrag و MouseDown/MouseMove است.
- `iePageHolder` از نوع `TImageEn` سطح اصلی نمایش/ویرایش تصویر است؛ رویدادهای ImageChange، DblClick و MouseDown/Move/Up دارد.
- یک Splitter بین پنل صفحات و فضای اصلی وجود دارد؛ بنابراین عرض پنل فهرست صفحات قابل تغییر است.
- `ThumZoomBar` از نوع TTrackBar با Min=40، Max=300 و Position=150 است و `ThumZoomBarChange` به آن متصل است. این کنترل در پنل فهرست صفحات قرار دارد؛ نقش دقیقش باید از handler بررسی شود.

### 2. ورود، حذف و چاپ
نوار ابزار سمت چپ شامل دکمه‌هایی با نام‌های:
- `tbtnDeletePage`
- `tbtnAddImgFile`
- `tbtnScanDoc`
- `tbtnPrint`

همگی از handler مشترک `itToolbarClick` استفاده می‌کنند. از نام و Hintها می‌توان حذف صفحه، افزودن فایل تصویر، اسکن سند و چاپ را شناسایی کرد؛ جزئیات dialogها و مسیر ذخیره‌سازی هنوز از DFM معلوم نیست.

### 3. ابزارهای نمایش و ویرایش
نوار `EditToolBar` شامل موارد زیر است:
- اندازه واقعی: `tbtnvActualSize`
- Fit ارتفاع: `tbtnvFitHeight`
- Fit عرض: `tbtnvFitWidth`
- Fit ناحیه قابل نمایش: `tbtnvFitClient`
- Zoom In / Zoom Out: `tbtnZoomIn`، `tbtnZoomOut`
- قلم: `ToolButton4` با Hint/Caption برابر `tbtnPen`
- Scroll/Pan: `tbtnScrool`
- Crop: `tbtnCrop`
- زاویه چرخش آزاد: `seDegree` از نوع TSpinEdit با مقدار اولیه 0 و `tbtnFreeRotate`
- Auto Orient: `tbtnAutoOrientor`
- چرخش ساعت‌گرد/پادساعت‌گرد: `tbtnRotateCW`، `tbtnRotateCCW`
- Flip افقی/عمودی: `tbtnFlipHor`، `tbtnFlipVer`
- انتخاب رنگ قلم: `btnSelectColor`
- اندازه قلم: `cbbPenSize` با handler مستقل `itSetPenSize`
- Undo / Redo: `tbtnUndo`، `tbtnRedo`

اکثر دکمه‌های ابزار به `itToolbarClick` متصل‌اند و Hintها از `itToolbarHint` و `itToolbarHintClear` استفاده می‌کنند. `btnSelectColor` نیز همین handler مشترک را دارد.

### 4. درج تصاویر در سند/مجموعه
- `rgInsertLocation` گروه «درج تصاویر جدید در» است.
- `rbPicInsert`: «درج در مکان جاری» و به‌صورت پیش‌فرض انتخاب شده.
- `rbPicAppend`: «افزودن به انتهای تصویر».
- هر دو RadioButton به `rbPicInsertClick` متصل‌اند.
- این UI نشان می‌دهد کاربر می‌تواند محل قرارگیری تصاویر جدید را بین موقعیت جاری و انتهای مجموعه انتخاب کند؛ معنای دقیق «تصویر/سند» و نحوه ادغام باید از کد handler و مدل داده روشن شود.

### 5. پیمایش صفحات
نوار پایین شامل:
- `btnFirstPage`، `btnPreviousPage`، `btnNextPage`، `btnLastPage`
- `edtPageN` برای شماره صفحه
- چهار دکمه پیمایش به `itNavigatePages` متصل‌اند.

### 6. پنل تنظیمات چاپ
پنل `pnlPrintSetting` در فضای اصلی قرار دارد و اجزای زیر را دارد:
- `grpPreview` با `imgenPrintPreview` از نوع TImageEn برای پیش‌نمایش.
- `grpMargin`: چهار فیلد `TDoubleEdit` برای بالا، پایین، چپ و راست؛ واحد Caption سانتی‌متر است. هر چهار فیلد به `onPrintParamsObjectChange` وصل‌اند.
- `grgPosition` با `cbbPosition` برای موقعیت؛ OnChange به `onPrintParamsObjectChange`.
- `grpSize` با `cbbSize` برای اندازه؛ OnChange به همان handler.
- `grpPrintRange` با `cbbPrintRang` برای محدوده چاپ.
- دکمه `btnPSOK` با عنوان «چاپ» و handler `btnPSOKClick`.
- دکمه `btnPSCancel` با عنوان «انصراف» و handler `btnPSCancelClick`.
- `btnPrinterSetup` با عنوان «تنظیمات پرینتر» و handler `btnPrinterSetupClick`.

نکته: وجود پنل تنظیمات چاپ در DFM تأیید شده، اما visible بودن آن در تمام زمان‌ها یا شرط نمایش آن از خروجی خلاصه‌شده properties به‌تنهایی قابل نتیجه‌گیری نیست.

### 7. دکمه‌های نهایی و اجزای غیرمرئی
- `btnOK`: «تایید و ارسال» با `btnOKClick`.
- `btnCancel`: «انصراف» با `btnCancelClick`.
- `Button2`: «ذخیره در فایل» با `Button2Click` و `Visible=false`.
- `ScrollTimer`: تایمر غیرفعال اولیه با `ScrollTimerTimer`.
- `iemioImageHandle` از نوع `TImageEnMIO` و `ImageEnIO1` از نوع `TImageEnIO`.
- `PrinterSetupDialog`: کامپوننت تنظیمات چاپگر.
- دو ImageList برای آیکون‌های نوار ابزار.

## وابستگی فنی مهم: ImageEn
در فرم، کلاس‌های اختصاصی زیر دیده می‌شوند:
- `TImageEn`
- `TImageEnMView`
- `TImageEnMIO`
- `TImageEnIO`

این‌ها نشانه قوی استفاده از خانواده کتابخانه ImageEn برای نمایش، مدیریت چندصفحه‌ای و I/O تصاویر است. این یافته با importها و شواهد قبلی ImageEn/WIA/TWAIN هم‌راستاست. DFM به‌تنهایی نسخه دقیق ImageEn یا تمام codecها/driverهای استفاده‌شده را مشخص نمی‌کند.

## پیامد برای نسخه بومی Linux
این فرم یک ماژول بزرگ و مستقل را مشخص می‌کند؛ بازسازی آن صرفاً با یک image viewer ساده کافی نیست. قابلیت‌های لازم برای specification و تست:
1. مدیریت مجموعه چندصفحه‌ای: افزودن، حذف، انتخاب، drag/drop و جابه‌جایی صفحات.
2. اتصال ورودی اسکنر و افزودن فایل تصویر، با تشخیص فرمت‌های واقعی مورد استفاده.
3. نمایش تصویر با zoom، pan، fit modes و پیمایش صفحه.
4. Crop، چرخش آزاد/زاویه‌ای، auto-orient، flip افقی/عمودی.
5. ابزار annotation با قلم، رنگ و ضخامت، به همراه Undo/Redo.
6. کنترل محل درج تصویر جدید: مکان جاری یا انتهای مجموعه.
7. چاپ با preview، چهار حاشیه بر حسب سانتی‌متر، موقعیت، اندازه و محدوده چاپ.
8. تنظیم چاپگر و مدیریت Cancel/Confirm/Send.
9. ذخیره و حفظ کیفیت، DPI، metadata و ترتیب صفحات؛ جزئیات باید با رفتار Windows سنجیده شود.

برای Linux می‌توان Qt را برای UI و Pillow/OpenCV و کتابخانه‌های تخصصی TIFF/PDF را برای پردازش ارزیابی کرد. برای ورودی اسکنر باید مسیرهای SANE/Linux بررسی شوند. این‌ها گزینه‌های جایگزین‌اند، نه ادعای سازگاری کامل با ImageEn؛ انتخاب نهایی پس از بررسی فرمت‌ها و handlerها انجام شود.

## موارد باز
- الگوریتم و semantics دقیق `itToolbarClick` برای هر ToolButton.
- ساختار داده چندصفحه‌ای و رابطه آن با اسناد/رکوردهای EMWAT.
- عملکرد دقیق Auto Orient و اینکه از EXIF یا تحلیل تصویر استفاده می‌کند.
- جزئیات Undo/Redo و اینکه history شامل چه عملیاتی است.
- رفتار واقعی اسکن: WIA/TWAIN، رزولوشن، رنگ، duplex، feeder و multi-page.
- جزئیات چاپ: مقیاس، fit، موقعیت، حاشیه‌ها، محدوده و خروجی نهایی.
- تفاوت `btnOK` «تایید و ارسال» با `Button2` پنهان «ذخیره در فایل».
- تعامل این فرم با `TfrmGScanPreview` و `TfrmSimpleImageEditor`.

## گام بعد
Decode کردن `RCDATA_TFRMSIMPLEIMAGEEDITOR_18.bin`؛ سپس مقایسه سه فرم اسکن/تصویر و ردیابی handlerهای `itToolbarClick`، `btnOKClick` و eventهای ImageEn در BPL. بعد از آن می‌توان specification قابل تست برای ماژول مدیریت اسکن و تصویر نوشت.
