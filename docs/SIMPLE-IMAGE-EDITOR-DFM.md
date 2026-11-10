# تحلیل فرم ویرایشگر ساده تصویر (TfrmSimpleImageEditor)

تاریخ: 2026-11-10  
منبع: `analysis-input/RCDATA_TFRMSIMPLEIMAGEEDITOR_18.bin` از `EmwatMethods.bpl1`  
روش: decode مستقیم Binary DFM با امضای `TPF0`؛ هیچ فایل اجرایی اجرا نشده است.

## اعتبارسنجی
- اندازه فایل: 11,451 بایت
- امضا: `TPF0`
- parser تمام 11,451 بایت را مصرف کرد؛ 0 بایت باقی‌مانده
- فرم ریشه: `TfrmSimpleImageEditor` / نمونه `frmSimpleImageEditor`
- تعداد اجزا: 19 (فرم + 18 کنترل/کامپوننت)
- عنوان: «پیش‌نمایش اسکن»
- ClientWidth=412، ClientHeight=453؛ راست‌چین و در مرکز صفحه

## ساختار رابط کاربری

### 1. نمایش تصویر
- `pnlImage` پنل میزبان تصویر است.
- `pbImgViewer` از نوع `TPaintBox` ناحیه اصلی نمایش تصویر است.
- رویدادهای `pbImgViewerPaint`، `pbImgViewerMouseDown`، `pbImgViewerMouseMove` و `pbImgViewerMouseUp` به PaintBox متصل‌اند.
- Double-click نیز به `doCommand` متصل است.
- این ساختار نشان می‌دهد رسم تصویر و بخشی از تعاملات اشاره‌گر به‌صورت سفارشی مدیریت می‌شوند؛ الگوریتم رسم و semantics دقیق drag از DFM معلوم نیست.

### 2. صفحه و ابزارها
گروه `grpPageAndTools` شامل:
- `cmbPages`: فهرست انتخاب صفحه، با `cmbPagesChange`. مقدار طراحی‌شده در DFM فقط «1» است و تعداد صفحات runtime از آن قابل استنباط نیست.
- `lblPagesCount`: برچسب «از 10» در مقدار طراحی‌شده؛ مقدار واقعی ممکن است در runtime تغییر کند.
- ابزارهای متصل به handler مشترک `doCommand`:
  - `btnRRotate`، Tag=11: چرخش ساعتگرد
  - `btnLRotate`، Tag=12: چرخش پادساعتگرد
  - `btnCrop`، Tag=13: برش تصویر
  - `btnHFilp`، Tag=14: وارونه‌سازی افقی
  - `btnVFlip`، Tag=15: وارونه‌سازی عمودی
  - `btnOriginalImage`، Tag=16: بازگشت به تصویر اصلی
- Tagهای 11 تا 16 شناسه فرمان‌های UI هستند؛ معنای داخلی و نحوه اجرای آن‌ها باید از کد `doCommand` تأیید شود.

### 3. خروجی و دکمه‌های نهایی
- `rgImageType`: گروه انتخاب TIFF یا JPEG؛ در DFM مقدار `Enabled=false` دارد.
- `chkForceSinglePage`: گزینه «ارسال هر صفحه به صورت یک فایل جدا»؛ در DFM غیرفعال است.
- غیرفعال بودن این کنترل‌ها در حالت طراحی ثابت است، نه لزوماً وضعیت نهایی runtime؛ فعال‌سازی احتمالی باید در handlerها بررسی شود.
- `btnRegister`: «تأیید و ارسال»، `ModalResult=1)، handler برابر `btnRegisterClick`.
- `btnCalncel`: «انصراف از ارسال»، `ModalResult=2)، handler برابر `btnCalncelClick`.
- فرم رویدادهای `FormCreate`، `FormActivate`، `FormClose` و `FormCloseQuery` را دارد.

## Component inventory
| نوع | نام | نقش |
|---|---|---|
| TPanel | pnlImage | میزبان ناحیه تصویر |
| TPaintBox | pbImgViewer | رسم تصویر و دریافت رویدادهای ماوس |
| TGroupBox | grpPageAndTools | گروه صفحه و ابزارها |
| TComboBox | cmbPages | انتخاب صفحه |
| TBitBtn | btnRRotate / btnLRotate | چرخش |
| TBitBtn | btnCrop | برش |
| TBitBtn | btnHFilp / btnVFlip | وارونه‌سازی افقی/عمودی |
| TBitBtn | btnOriginalImage | بازگشت به تصویر اصلی |
| TRadioGroup | rgImageType | TIFF/JPEG |
| TCheckBox | chkForceSinglePage | ارسال هر صفحه به‌صورت فایل مستقل |
| TBitBtn | btnRegister / btnCalncel | تأیید و انصراف |
| TXPManifest | xpm | کامپوننت manifest |

## مقایسه با دو فرم مرتبط

| قابلیت | TfrmGScanPreview | TfrmSimpleImageEditor | TfrmImageTools |
|---|---|---|---|
| نمایش تصویر | PaintBox | PaintBox | TImageEn |
| انتخاب صفحه | ComboBox | ComboBox | نمای چندصفحه‌ای و پیمایش |
| Rotate / Flip | دارد | دارد | دارد |
| Crop | دارد | دارد | دارد |
| بازگشت به اصل | دارد | دارد | Undo/Redo و ابزارها |
| TIFF/JPEG | انتخاب خروجی | انتخاب خروجی، کنترل‌ها در DFM غیرفعال | از طریق I/O/چاپ؛ جزئیات نامشخص |
| اسکن/ورود فایل | از مسیر workflow اسکن | در DFM صریح نیست | ورود فایل و اسکن صریح |
| مدیریت مجموعه صفحات | محدود/نامشخص | انتخاب صفحه | مدیریت کامل صفحات |
| چاپ | در DFM صریح نیست | در DFM صریح نیست | پنل تنظیمات چاپ |

این مقایسه صرفاً بر پایه DFMهای decodeشده است. وجود کنترل یا handler به‌تنهایی رفتار نهایی runtime را اثبات نمی‌کند.

## پیامد برای بازسازی بومی Linux
این فرم به‌نظر یک ویرایشگر سبک برای اصلاح تصویر/صفحه پیش از تأیید و ارسال است، در حالی‌که `TfrmImageTools` محیط جامع مدیریت، ورود، ویرایش و چاپ مجموعه تصاویر است و `TfrmGScanPreview` رابط پیش‌نمایش/اصلاح در مسیر اسکن را ارائه می‌کند. این تفکیک نقش، فرضیه‌ای قوی بر پایه نام‌ها و UI است و باید با call graph و handlerها تأیید شود.

حداقل نیازهای قابل تست برای این فرم:
1. نمایش تصویر و مدیریت repaint/resize.
2. انتخاب صفحه جاری از مجموعه ورودی.
3. چرخش 90 درجه در هر دو جهت.
4. برش با تعامل ماوس.
5. Flip افقی و عمودی.
6. بازگشت به نسخه اصلی بدون تخریب داده اولیه.
7. خروجی TIFF/JPEG و امکان split هر صفحه به فایل مستقل، در صورت فعال بودن گزینه در runtime.
8. رفتار دقیق تأیید/انصراف و تحویل خروجی به workflow فراخوان.

برای پیاده‌سازی بومی می‌توان UI مبتنی بر Qt و پردازش تصویر با Pillow/OpenCV و کتابخانه مناسب TIFF را ارزیابی کرد. این‌ها گزینه‌های جایگزین پیشنهادی‌اند و سازگاری با رفتار اصلی هنوز اثبات نشده است.

## موارد باز و گام بعد
- پیاده‌سازی `doCommand` و mapping دقیق Tagهای 11 تا 16.
- منطق بارگذاری تصویر و پر کردن `cmbPages` و `lblPagesCount`.
- شرایط فعال‌سازی انتخاب TIFF/JPEG و `chkForceSinglePage`.
- قرارداد `btnRegisterClick`: آیا تصویر را به فرم والد برمی‌گرداند، ذخیره می‌کند یا به سند متصل می‌کند؟
- ارتباط دقیق این فرم با `TfrmGScanPreview` و `TfrmImageTools`.
- کیفیت، DPI، metadata، چندصفحه‌ای بودن TIFF و نام‌گذاری فایل‌های جدا.

گام بعدی: مقایسه و ردیابی handlerهای `doCommand`، `btnRegisterClick` و رویدادهای Paint/Mouse در `EmwatMethods.bpl1`؛ سپس تدوین specification و تست‌کیس‌های ماژول بومی اسکن/تصویر.
