# EMWAT Office / COM / ProgID analysis
تاریخ: 2026-11-10
منابع: `EMWAT-Analysis-Results.txt` و فایل‌های strings موجود در مخزن
روش: جست‌وجوی ایستای نمادها و رشته‌ها؛ بدون اجرای COM و بدون دسترسی به Registry سیستم نصب‌شده.
وضعیت: شواهد بسیار قوی برای Office Automation؛ ProgID/CLSIDهای واقعی و نسخه‌های Office هدف هنوز استخراج نشده‌اند.

## 1. کشف مهم: Office Automation از حالت «احتمال» به «شواهد قوی» ارتقا یافت

در نمادهای `EmwatMethods.bpl1` مجموعه گسترده‌ای از wrapperها و type informationهای Delphi برای Word و Excel دیده می‌شود. موارد شاخص:

### Excel
- `TExcelApplication`
- `TExcelWorkbook`
- `TExcelWorksheet`
- `TExcelGlobal`
- `TExcelOLEObject`
- `TEditExcelWorkBook`
- `Workbooks`, `Worksheets`, `ActiveWorkbook`, `ActiveSheet`, `Range`, `Cells`
- `TExcelApplication.Get_Workbooks`, `TExcelApplication.Get_Worksheets`
- `TExcelWorkbook.Get_FileFormat`, `Get_Password`, `Get_ReadOnly`, `Get_VBProject`
- `TExcelWorksheet.Get_Range`, `Get_Cells`, `Get_UsedRange`

این‌ها به مدل شیء Excel Automation شباهت مشخص دارند و وجود لایه wrapper مربوط به Excel را با اطمینان بالا نشان می‌دهند.

### Word
- `TWordApplication`
- `TWordDocument`
- `TWordParagraphFormat`
- `TEditWordDocument`
- `ActiveDocument`, `Bookmarks`, `FormFields`, `Paragraphs`, `Signatures`, `MailMerge`
- `TWordApplication.Get_ActiveDocument`, `Get_Browser`, `Get_Version`
- `TWordDocument.Get_Content`, `Get_Bookmarks`, `Get_FormFields`, `Get_Signatures`
- رشته خطا: `Error on insert sign to word document. Exception:`

این شواهد از وجود wrapperهای Word Automation و workflowهایی مانند دستکاری سند، bookmark/form field و درج امضا پشتیبانی می‌کنند.

### COM infrastructure
- `TOleServer.GetAutoConnect`
- `TOleServer.GetConnectKind`
- `TOleServer.SetAutoConnect`
- `COMAddIn.Get_ProgId`, `COMAddIns.Get_Count`
- `OLEFormat.Get_ProgID`
- `_CommandBarActiveX.Get_ControlCLSID`
- `OfficeDataSourceObject`
- `OfficeXP`

این نمادها نشان‌دهنده استفاده از Delphi OLE Automation wrappers و دسترسی به COM add-in / OLE object metadata هستند.

## 2. نتیجه‌گیری و سطح اطمینان

| پرسش | نتیجه فعلی | اطمینان |
|---|---|---|
| آیا COM/OLE استفاده شده؟ | بله؛ Agent imports و نمادهای Methods پشتیبانی می‌کنند. | بسیار بالا |
| آیا Word Automation وجود دارد؟ | بله؛ wrapperها و interface/typeinfoهای Word در Methods دیده می‌شوند. | بسیار بالا |
| آیا Excel Automation وجود دارد؟ | بله؛ wrapperها و مدل شیء Excel در Methods دیده می‌شوند. | بسیار بالا |
| آیا workflow امضا در Word وجود دارد؟ | رشته خطای درج امضا وجود دارد؛ رفتار کامل هنوز runtime-validated نیست. | متوسط رو به بالا |
| ProgID دقیق چیست؟ | هنوز از رشته‌های استخراج‌شده قطعی نشده است. | نامشخص |
| CLSID دقیق چیست؟ | GUID صریح مرتبط با Office در گزارش تجمیع‌شده پیدا نشد. | نامشخص |
| نسخه Office هدف چیست؟ | `OfficeXP` در نمادها وجود دارد، اما این نام namespace/type library است و به‌تنهایی نسخه نصب‌شده یا حداقل نسخه موردنیاز را ثابت نمی‌کند. | نامشخص |
| آیا Browser نماد embedded IE/WebBrowser است؟ | خیر؛ `TWordApplication.Get_Browser` با object model خود Word سازگار است و نباید آن را شاهد کنترل مرورگر تعبیه‌شده تلقی کرد. | اصلاح برداشت قبلی |

## 3. مرورگر تعبیه‌شده: اصلاح یک سرنخ

نماد `Browser@Get_Parent` و `TWordApplication.Get_Browser` در کنار typeinfoهای Word دیده شده‌اند. بنابراین محتمل‌ترین تفسیر این است که این Browser متعلق به Word object model است، نه الزاماً کنترل ActiveX مرورگر ویندوز.

شواهد قبلی bridge جاوااسکریپتی `postMessage` و تنظیمات IE در `Emwat.reg` همچنان وجود دارند؛ اما موتور UI/Browser هنوز شناسایی نشده است. برای اثبات WebBrowser/IE host باید CLSIDهای کنترل، کلاس‌های پنجره، resourceها، registry registration یا runtime evidence پیدا شوند.

## 4. چرا CLSID/ProgID هنوز قطعی نیست؟

جست‌وجوی رشته‌ای روی گزارش تجمیع‌شده، نام‌های کلاس و propertyهای COM را یافته، اما GUIDهای قابل انتساب به Word/Excel یا literalهایی مانند `Word.Application` و `Excel.Application` را تأیید نکرده است. ممکن است:
- ProgIDها در runtime ساخته یا از Registry خوانده شوند؛
- Delphi type library wrapperها GUIDها را در ساختارهای binary/typeinfo نگه دارند نه به شکل رشته متنی؛
- COM activation از CLSID ثابت یا registered type library استفاده کند؛
- اطلاعات activation در Installer/Registry/فایل‌های جانبی باشد.

عدم مشاهده literal در strings به معنی نبود COM activation نیست.

## 5. پیامد برای بازسازی Linux

1. Office compatibility یک قابلیت محوری است و نباید به تبدیل ساده فایل محدود شود.
2. قراردادهای واقعی Word/Excel باید به workflowهای مستقل تبدیل شوند: بازکردن/ساخت سند، bookmark و form field، درج امضا، خواندن/نوشتن سلول و range، sheet management، قالب‌بندی و ذخیره.
3. LibreOffice UNO گزینه اصلی بررسی برای پیاده‌سازی بومی این workflowهاست؛ اما هر عملیات باید با نمونه واقعی و regression tests سنجیده شود.
4. اگر قالب‌های Word/Excel شامل macro، ActiveX، OLE embedding یا امضای دیجیتال باشند، سازگاری ممکن است محدودیت داشته باشد و باید جداگانه تست شود.
5. به‌دلیل PE32/x86 بودن اجزای Windows، registry view سی‌ودوبیتی و نسخه Office نصب‌شده در محیط اصلی می‌تواند مهم باشد.

## 6. اقدام بعدی: استخراج بیشتر

از کاربر بخواه گزارش تکمیلی را با اسکریپت `EMWAT-COM-Resource-Analyzer.py` بسازد. اسکریپت باید:
- همه فایل‌های زیر `D:\EmwatInstaller` را اسکن کند؛
- GUIDها و ProgIDهای محتمل را با نام فایل و context استخراج کند؛
- resource directory فایل‌های PE را فهرست کند و resourceهای manifest/dialog/string/RCDATA/HTML/version را استخراج کند؛
- فقط فایل‌های فنی را گزارش کند و داده‌های مشتری/اسناد واقعی را وارد مخزن نکند.

سپس با رجیستری محیط نصب‌شده و (در صورت وجود) `Emwat.reg` مقایسه شود. از export کل Registry یا اطلاعات حساب کاربری خودداری شود.

## 7. مراجع فنی COM
- Microsoft Learn, COM Registry Keys: https://learn.microsoft.com/en-us/windows/win32/com/com-registry-keys
- Microsoft Learn, CLSID Key: https://learn.microsoft.com/en-us/windows/win32/com/clsid-key-hklm
- Microsoft Learn, ProgID Key: https://learn.microsoft.com/en-us/windows/win32/com/-progid--key
- Microsoft Learn, InprocServer32: https://learn.microsoft.com/en-us/windows/win32/com/inprocserver32
