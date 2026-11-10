# تحلیل فرم تنظیمات چاپ Word (TfrmWordPrintOption)

## منبع و روش
- منبع: `analysis-input/RCDATA_TFRMWORDPRINTOPTION_19.bin` در مخزن خصوصی.
- اندازه: 88,487 بایت.
- امضای ابتدای stream: `TPF0`؛ Binary DFM.
- parser ساختار component stream را به‌صورت بازگشتی خواند؛ تمام 88,487 بایت مصرف شد و خطای ساختاری/بایت باقی‌مانده وجود نداشت.
- تعداد کل componentها: 34 (فرم اصلی + 33 کنترل/کامپوننت فرزند).
- توجه: این خروجی ساختار و propertyهای ذخیره‌شده در DFM را نشان می‌دهد؛ منطق پیاده‌سازی event handlerها در کد Delphi است و از خود DFM قابل بازیابی نیست.

## مشخصات فرم
- کلاس/نام: `TfrmWordPrintOption / frmWordPrintOption`
- عنوان: «تنظیمات چاپ»
- ClientWidth: 633
- ClientHeight: 479
- BiDiMode: `bdRightToLeft`
- BorderStyle: `bsToolWindow`
- Position: `poDesktopCenter`
- رویدادهای فرم: `OnActivate=FormActivate`, `OnCreate=FormCreate`, `OnDestroy=FormDestroy`
- `Icon.Data` شامل 82,726 بایت داده آیکون است؛ این حجم بزرگ بخش عمده اندازه resource را تشکیل می‌دهد و محتوای اجرایی/منطق برنامه نیست.

## ساختار کنترل‌ها و قابلیت‌های قابل مشاهده

| نام کنترل | کلاس | متن/عنوان | نقش و شواهد |
|---|---|---|---|
| `GroupBox1` | TGroupBox | چاپگر | بخش انتخاب چاپگر |
| `Label1` | TLabel | نام چاپگر: | برچسب انتخاب چاپگر |
| `cboPrinterName` | TComboBox | — | فهرست کشویی چاپگرها؛ `csDropDownList` |
| `Label2` | TLabel | رونوشت گیرندگان: | عنوان لیست رونوشت |
| `Label6` | TLabel | گیرندگان: | عنوان لیست گیرندگان |
| `lblSelAll` | TLabel | همه | انتخاب همه گیرندگان؛ `OnClick=lblSelAllClick` |
| `lblNone` | TLabel | هیچکدام | لغو انتخاب گیرندگان؛ `OnClick=lblNoneClick` |
| `lblSelAllCC` | TLabel | همه | انتخاب همه رونوشت‌ها؛ `OnClick=lblSelAllCCClick` |
| `lblNoneCC` | TLabel | هیچکدام | لغو انتخاب رونوشت‌ها؛ `OnClick=lblNoneCCClick` |
| `clbLetterReceivers` | TCheckListBox | — | فهرست انتخابی گیرندگان نامه |
| `clbLetterCC` | TCheckListBox | — | فهرست انتخابی رونوشت‌ها |
| `chkPrintCCToMain` | TCheckBox | چاپ رونوشت گیرندگان در نامه‌های اصلی | گزینه چاپ رونوشت در نامه اصلی؛ `OnClick=chkPrintCCToMainClick` |
| `chkPrintSelectedCCToMain` | TCheckBox | فقط رونوشت گیرندگان انتخاب شده درج شوند | محدودکردن درج رونوشت به موارد انتخاب‌شده |
| `grbPageRange` | TGroupBox | محدوده صفحات | تنظیم محدوده صفحات چاپ |
| `rdbAll` | TRadioButton | کلیه صفحات | انتخاب همه صفحات؛ پیش‌فرض Checked |
| `rdbCurrentPage` | TRadioButton | صفحه جاری | چاپ صفحه جاری |
| `rdbRange` | TRadioButton | صفحات: | چاپ بازه/صفحات انتخابی |
| `edtPages` | TEdit | — | ورود شماره صفحات؛ `OnKeyPress=edtPagesKeyPress`, `OnKeyUp=edtPagesKeyUp` |
| `Label4` | TLabel | شماره صفحه‌ها و یا محدوده صفحه‌ها را به صورت لاتین وارد نمایید. برای مثال، | راهنمای قالب ورود صفحات |
| `Label5` | TLabel | 2,3,5-10 | نمونه ورودی صفحات |
| `grbCopy` | TGroupBox | کپی | تنظیم تعداد نسخه‌ها |
| `chkCopyMain` | TCheckBox | نسخه به تفکیک گیرنده اصلی ... تعداد: | فعال‌سازی نسخه برای هر گیرنده اصلی؛ پیش‌فرض Checked؛ `OnClick=chkCopyMainClick` |
| `speCntCopyMain` | TSpinEdit | — | تعداد نسخه گیرنده اصلی؛ حداقل 1، حداکثر 200، پیش‌فرض 1 |
| `chkCopyCC` | TCheckBox | نسخه به تفکیک رونوشت گیرندگان ... تعداد: | نسخه برای رونوشت‌ها؛ `OnClick=chkCopyCCClick` |
| `speCntCopyCC` | TSpinEdit | — | تعداد نسخه رونوشت؛ 1 تا 200؛ در DFM غیرفعال |
| `chkCopyArchive` | TCheckBox | نسخه بایگانی ... تعداد: | نسخه بایگانی؛ `OnClick=chkCopyArchiveClick` |
| `speCntCopyArchive` | TSpinEdit | — | تعداد نسخه بایگانی؛ 1 تا 200؛ در DFM غیرفعال |
| `chkCopySelected` | TCheckBox | نسخه انتخابی ... تعداد: | نسخه انتخابی؛ `OnClick=chkCopySelectedClick` |
| `speCntCopySelected` | TSpinEdit | — | تعداد نسخه انتخابی؛ 1 تا 200؛ در DFM غیرفعال |
| `chkSaveSettings` | TCheckBox | انتخاب‌ها و تعداد آنها را به خاطر بسپار | گزینه ذخیره انتخاب‌ها و تعدادها |
| `btnOk` | TButton | تایید | دکمه تأیید؛ `Default=true`, `OnClick=btnOkClick` |
| `btnCancle` | TButton | انصراف | لغو؛ `Cancel=true`, `ModalResult=2` |

## برداشت‌های عملکردی
1. فرم چاپ فقط انتخاب چاپگر نیست؛ کنترل گیرندگان و CC، محدوده صفحات و تعداد نسخه‌های مختلف را نیز مدیریت می‌کند.
2. دو CheckListBox جداگانه برای گیرندگان اصلی و رونوشت‌ها وجود دارد؛ هر دو دارای عملیات انتخاب همه/هیچکدام هستند.
3. سه حالت محدوده چاپ دیده می‌شود: همه صفحات، صفحه جاری و صفحات مشخص. نمونه syntax برابر `2,3,5-10` است؛ parser واقعی ورودی هنوز باید از کد event handler استخراج یا با رفتار برنامه آزموده شود.
4. گزینه‌های تعداد نسخه شامل گیرنده اصلی، رونوشت، بایگانی و نسخه انتخابی هستند؛ هر SpinEdit دامنه 1 تا 200 دارد.
5. ذخیره انتخاب‌ها/تعدادها با `chkSaveSettings` در UI قابل مشاهده است؛ محل و قالب ذخیره‌سازی هنوز مشخص نیست.
6. وجود event handlerها، اتصال رویداد را اثبات می‌کند نه منطق داخلی آن‌ها؛ برای فهم رفتار باید کدهای `FormActivate`, `btnOkClick`, `chkCopy*Click`, `edtPagesKey*` و سایر handlerها در BPL تحلیل شوند.

## پیامد برای نسخه Linux
- یک پنجره «تنظیمات چاپ» با بخش چاپگر، گیرندگان/رونوشت‌ها، محدوده صفحات و تنظیم تعداد نسخه‌ها لازم است.
- مدل داده پیشنهادی باید انتخاب گیرندگان اصلی و CC، گزینه چاپ CC در نامه اصلی، حالت صفحه، عبارت صفحات، تعداد نسخه‌ها برای چهار دسته و گزینه حفظ تنظیمات را جدا نگه دارد.
- رفتارهای چاپ Word باید مستقل از UI پیاده‌سازی شوند تا بعداً backend چاپ/تولید سند Linux (از جمله LibreOffice در صورت تأیید تست سازگاری) قابل جایگزینی باشد.
- این DFM به‌تنهایی ثابت نمی‌کند تمام عملیات چاپ EMWAT فقط از طریق Word انجام می‌شود؛ فقط ساختار همین فرم را اثبات می‌کند.

## محدودیت‌ها و گام بعدی
- فایل حاوی آیکون بزرگ است؛ آیکون استخراج/منتشر نشده و داده خام آن در این سند درج نشده است.
- مقادیر runtime مانند محتوای واقعی فهرست گیرندگان/چاپگرها در DFM نیستند.
- گام بعد: DFM فرم‌های `TFRMGSCANPREVIEW`, `TFRMIMAGETOOLS` و `TFRMSIMPLEIMAGEEDITOR` را با همین parser decode کن؛ سپس event handlerها را به کدهای BPL پیوند بده.
