# تحلیل فرم پیش‌نمایش اسکن (TfrmGScanPreview)

تاریخ: 2026-11-10  
منبع: `analysis-input/RCDATA_TFRMGSCANPREVIEW_13.bin` از `EmwatMethods.bpl1`  
روش: decode مستقیم Binary DFM با امضای `TPF0`؛ هیچ فایل اجرایی اجرا نشده است.

## اعتبارسنجی فایل
- اندازه: 49,193 بایت
- امضا: `TPF0`
- parser تمام 49,193 بایت را مصرف کرد؛ 0 بایت باقی‌مانده
- فرم ریشه: `TfrmGScanPreview` / نام نمونه `frmGScanPreview`
- تعداد اجزا: 25 (فرم + 24 کنترل/کامپوننت)

## مشخصات فرم
- عنوان: `Image Preview ...`
- ClientWidth: 500، ClientHeight: 437
- Position: `poDesktopCenter`
- رویدادهای فرم: `FormActivate`، `FormCreate`، `FormDestroy`، `FormShow`

## ساختار و رفتار قابل استنباط از DFM

### نمایش تصویر و تعامل
- `pnlImage`: پنل میزبان تصویر، حدود 487×367
- `PaintBox`: ناحیه رسم تصویر، حدود 476×355
- رویدادها:
  - `PaintBoxPaint`: رسم/بازرسم تصویر
  - `PaintBoxMouseDown`، `PaintBoxMouseMove`، `PaintBoxMouseUp`: تعامل اشاره‌گر با تصویر؛ احتمالاً برای انتخاب ناحیه/برش یا جابه‌جایی، اما semantics دقیق باید از handler تأیید شود.
  - `doCommand` روی double-click ناحیه PaintBox نیز متصل است.

### ابزارهای ویرایش
در نوار ابزار، دو مجموعه کنترل برای ابزارها وجود دارد:
- کنترل‌های گرافیکی `TImage`: `uibtnRRotate`، `uibtnLRotate`، `uibtnCrop`، `uibtnHFlip`، `uibtnVFlip`، `uibtnOrginalImage`.
- کنترل‌های دکمه‌ای `TBitBtn`: `BitBtnRRotate`، `BitBtnLRotate`، `BitBtnCrop`، `BitBtnHFilp`، `BitBtnVFlip`، `BitBtnOriginalImage`.
- فرمان‌ها به handler مشترک `doCommand` متصل‌اند.
- Hintها به‌ترتیب عملیات را مشخص می‌کنند: Rotate Clockwise، Rotate Counterclockwise، Crop، Horizontal Flip، Vertical Flip، Original Image.
- دو کنترل Original Image در DFM با `Visible=false` تعریف شده‌اند؛ احتمالاً نسخه جایگزین/نمایش شرطی UI هستند، اما زمان و شرط نمایش از DFM معلوم نیست.

وجود هر دو خانواده TImage و TBitBtn برای ابزارهای مشابه احتمالاً نشان‌دهنده دو مسیر/نسخه UI یا کنترل‌های موازی است؛ بدون بررسی کد handler نباید فرض کرد هر دو هم‌زمان نمایش داده می‌شوند یا عملکرد مستقل دارند.

### صفحات و قالب خروجی
- `cmbPages`: فهرست صفحه‌ها؛ رویداد `cmbPagesChange`.
- `rbtnTiff`: گزینه TIFF و به‌صورت پیش‌فرض Checked.
- `rbtnJepeg`: گزینه JPEG.
- در نتیجه فرم دست‌کم انتخاب صفحه و انتخاب قالب TIFF/JPEG را در UI ارائه می‌کند. نحوه ذخیره/ثبت خروجی و کیفیت/فشرده‌سازی از DFM قابل تعیین نیست.

### دکمه‌ها
- `uibtnCancel` و `uibtnRegister`: کنترل‌های TImage با رویدادهای `uibtnCancelClick` و `uibtnRegisterClick`.
- `BitBtnCalncel`: رویداد `BitBtnCalncelClick`.
- `BitBtnRegister`: رویداد `BitBtnRegisterClick`.
- `btnOk` و `btnCancel` دو TBitBtn پنهان هستند؛ در این DFM handler ثبت‌شده‌ای برایشان دیده نشد.
- `XPManifest1`: کامپوننت manifest قدیمی VCL.

## Component inventory
| نوع | نام | نقش/رویداد مهم |
|---|---|---|
| TPanel | pnlImage | میزبان تصویر |
| TPaintBox | PaintBox | نمایش و تعامل؛ Paint/Mouse handlers |
| TPanel | ToolPanel | نوار ابزار گرافیکی |
| TPanel | BtnToolPanel | نوار ابزار دکمه‌ای |
| TComboBox | cmbPages | انتخاب صفحه؛ cmbPagesChange |
| TRadioButton | rbtnTiff / rbtnJepeg | قالب خروجی |
| TImage | uibtnRRotate / uibtnLRotate / uibtnCrop / uibtnHFlip / uibtnVFlip | ابزارهای تصویر با doCommand |
| TBitBtn | BitBtnRRotate / BitBtnLRotate / BitBtnCrop / BitBtnHFilp / BitBtnVFlip | ابزارهای تصویر با doCommand |
| TImage / TBitBtn | کنترل‌های Original Image | بازگشت به تصویر اصلی؛ پنهان در DFM |
| TImage / TBitBtn | کنترل‌های Cancel و Register | خروج/ثبت، handlerهای جداگانه |
| TBitBtn | btnOk / btnCancel | کنترل‌های پنهان |
| TXPManifest | XPManifest1 | سازگاری ظاهری VCL |

## نیازهای بازسازی بومی Linux
این DFM فقط UI و اتصال eventها را ثابت می‌کند، نه الگوریتم پردازش تصویر. پیاده‌سازی بومی باید حداقل این رفتارها را با تست مستقل پوشش دهد:
1. نمایش چندصفحه‌ای سند/تصویر و جابه‌جایی بین صفحات.
2. چرخش 90 درجه در هر دو جهت، با حفظ کیفیت و ابعاد منطقی.
3. برش با انتخاب ناحیه توسط pointer و امکان تأیید/لغو.
4. Flip افقی و عمودی.
5. بازگردانی دقیق به تصویر اصلی، بدون تجمع تغییرات ناخواسته.
6. خروجی TIFF و JPEG؛ پارامترهای کیفیت و چندصفحه‌ای بودن باید از رفتار نسخه اصلی استخراج شوند.
7. Cancel/Register و ارتباط آن‌ها با workflow اسکن/ثبت سند باید از handlerها مشخص شود.

در پیاده‌سازی احتمالی Python می‌توان Qt برای UI و Pillow/OpenCV یا کتابخانه مناسب TIFF برای پردازش تصویر را ارزیابی کرد؛ این صرفاً گزینه فنی اولیه است و هنوز تصمیم معماری نهایی نیست.

## موارد نامشخص و گام بعد
- معنای دقیق `Register` و اینکه خروجی را ذخیره، ضمیمه یا به رکوردی متصل می‌کند.
- آیا TIFF خروجی چندصفحه‌ای است یا فقط صفحه جاری را صادر می‌کند.
- جزئیات crop، مختصات، zoom، fit-to-window و حفظ DPI.
- چرا دو مجموعه TImage و TBitBtn برای ابزارها وجود دارد و کدام در runtime فعال می‌شود.
- ارتباط این فرم با اسکنر/WIA/TWAIN و `TFRMIMAGETOOLS` / `TFRMSIMPLEIMAGEEDITOR`.

گام بعدی: decode کردن `RCDATA_TFRMIMAGETOOLS_14.bin` و سپس `RCDATA_TFRMSIMPLEIMAGEEDITOR_18.bin`؛ پس از آن handlerهای `doCommand` و Paint/Mouse را در BPL به این UI متصل می‌کنیم.
