# تحلیل ایستای پروتکل Word و connectorهای EMWAT

تاریخ: 2026-11-12  
منبع: RTTI/symbol strings استخراج‌شده از EmwatMethods.bpl1-strings.txt  
روش: جست‌وجوی نمادها و type information؛ بدون اجرای برنامه و بدون مشاهده payload واقعی شبکه.  
وضعیت: شواهد ساختاری قوی؛ قرارداد wire هنوز runtime-validated نیست.

## 1. کشف مهم: Word workflow یک connector مشخص دارد

در BPL این کلاس‌ها و متدها دیده می‌شوند:

- Emwatconnector.TEditWordDocument.PerformMethod
- Emwatconnector.TCompareWordDocument.PerformMethod
- Emwatmethod.TEmwatMethod.Invoke
- Emwatmethod.TEmwatMethod.PerformMethod
- Emwatmethod.ParamsToXML
- Wordviewer.OpenDoc که یک TEmwatInvokeParam دریافت می‌کند.

این ساختار با یک لایه dispatch سازگار است: درخواست عمومی به پارامترها تبدیل می‌شود، سپس connector مناسب عملیات Word را اجرا می‌کند. ParamsToXML یک نام متد صریح برای تبدیل dictionary پارامترها به XML است؛ مسیر تبدیل معکوس و ساختار envelope هنوز از این فهرست نمادها به‌تنهایی معلوم نیست. با این حال، نام دقیق متد wire، کلیدهای ورودی و mapping آن‌ها به کلاس‌ها هنوز از این نمادها به‌تنهایی معلوم نیست.

## 2. ساختارهای XML مربوط به Word

نوع‌های تولیدشده در Wordrequestxml و Wordresponsexml چند بخش مهم را آشکار می‌کنند.

### Word request

Wordrequestxml.TXMLWorddocumentType دارای propertyهای زیر است:
- Body
- Fields
- Optionalattributes
- Permission
- Requestedtypes
- Settings
- Status
- ViewMode

Wordrequestxml.TXMLFieldsType یک collection از Fieldها و Wordrequestxml.TXMLSettingsType یک collection از Settingهاست. Wordrequestxml.TXMLBodyType نیز property مربوط به Encryption دارد.

Wordrequestxml.TXMLFieldType دارای:
- Id
- Concator
- Mimetype
- Separator
- Encryption

Wordrequestxml.TXMLStyleType دارای:
- Align
- FontName
- FontSize
- FontStyle
- Valign

این موارد نشان می‌دهند درخواست Word صرفاً یک رشته متن ساده نیست و یک مدل XML ساخت‌یافته برای بدنه سند، فیلدها، تنظیمات و style وجود دارد. body، fieldها و نوع‌های خروجی metadata مربوط به MIME type و encryption نیز دارند؛ بنابراین باید احتمال payloadهای باینری/رمزشده را در تحلیل بعدی در نظر گرفت، بدون اینکه فعلاً فرمت یا الگوریتم خاصی فرض شود. معنای دقیق هر property، الزامی‌بودن آن و ساختار XML نهایی باید با نمونه request واقعی تأیید شود.

### Word response

Wordresponsexml.TXMLResponseWordType دارای:
- Status
- ErrorCode
- Returntypes

Wordresponsexml.TXMLTypeType دارای:
- Encryption
- Mimetype

همچنین توابع GetResponseWord، LoadResponseWord و NewResponseWord دیده می‌شوند. این شواهد وجود مدل XML پاسخ را نشان می‌دهند؛ اما نوع محتوای return، قرارداد خطا و نحوه انتقال فایل هنوز روشن نیست.

## 3. عملیات و lifecycle سند Word

در Wordviewer.TWordViwer این متدها/handlerها دیده می‌شوند:

- OpenDoc
- LoadDocument
- PrepareDocument
- ProtectDocument
- FillField و FillImageField
- FillMSWFields و FillPrintDocFields
- AddImagesToDoc
- AddXmlWordConfigFieldsToDic
- CollectFieldsSets
- GetFieldValue و SetFieldValue
- GetXmlFieldInfo
- AddCustomDocPropertiesToDic
- StoreFieldValuesForPrint
- SilentSaveEmwatDoc
- OnTmrAutoSave
- WordAppDocumentBeforeClose
- WordAppDocumentBeforeSave
- WordAppDocumentBeforePrint
- WordAppNewDocument
- QuitWord

### برداشت محتاطانه

وجود SilentSaveEmwatDoc، OnTmrAutoSave و handlerهای BeforeClose/BeforeSave نشان می‌دهد چرخه ذخیره‌سازی و بسته‌شدن سند در خود EMWAT مدیریت می‌شود و مسیر silent-save/autosave وجود دارد. این یافته با تجربه کاربر درباره بازگشت سند پس از بستن Word سازگار است، اما هنوز ثابت نمی‌کند که هر تغییر ذخیره‌نشده‌ای حتماً به اتوماسیون ارسال می‌شود یا ارسال دقیقاً در کدام event رخ می‌دهد.

## 4. Connectorهای دیگر کشف‌شده

علاوه بر Word، این connectorها نیز در Emwatconnector دیده می‌شوند:

- TEditExcelWorkBook
- TCompareWordDocument
- TFaxDocument
- TImageEdition
- TScanDocument
- TGetEmwatVersion
- TSetEmwatVersion
- TShowEmwatSetting
- TShowLastEditedDocs
- TShowSendLog
- TUpgradeEmwat

این فهرست وجود مسیرهای جداگانه برای Excel، مقایسه Word، فکس، ویرایش تصویر، اسکن، تنظیمات و گزارش اسناد اخیر/ارسال را نشان می‌دهد. این‌ها نام کلاس‌های dispatch هستند، نه تضمین اینکه تمام قابلیت‌ها در هر نصب فعال یا مورد استفاده باشند.

## 5. پیامد معماری Linux

1. پیاده‌سازی باید یک dispatcher مستقل داشته باشد و عملیات Word را از scan/image/fax/Excel جدا کند.
2. مدل Word باید دست‌کم مفاهیم Document، Body، Fields، Settings، Permission، ViewMode، RequestedTypes و Style را پوشش دهد؛ schema نهایی فقط پس از گرفتن نمونه XML واقعی تثبیت شود.
3. برای LibreOffice باید adapter جداگانه طراحی شود؛ mapping فیلدها و styleها نباید در HTTP layer دفن شود.
4. چرخه autosave/close باید به state machine مستقل تبدیل شود: opened، dirty، saving، closing، returned، failed/cancelled. transitionها پس از runtime trace قطعی شوند.
5. connectorهای ScanDocument و ImageEdition باید در معماری باقی بمانند؛ توسعه آن‌ها پس از روشن‌شدن contract اصلی Word و bridge ادامه یابد.
6. هیچ XML نمونه یا payload فرضی نباید به‌عنوان پروتکل واقعی معرفی شود.

## 6. گام بعد برای اثبات قرارداد

برای یک نامه آزمایشی با داده ساختگی در الماس گام، باید این داده‌ها ثبت شوند:
- پیام postMessage اولیه و body درخواست POST، با حذف token/cookie و محتوای شخصی.
- نام/مقدار پارامترهای Word request و encoding.
- پاسخ خام سرویس و content type/status.
- فایل موقت ساخته‌شده و پسوند آن، بدون محتوای محرمانه.
- زمان اجرای autosave، Save، BeforeClose و بازگشت نتیجه.
- تفاوت سناریوی Save صریح با بستن بدون Save.

تا قبل از این آزمایش، پیاده‌سازی سازگار Linux باید از حدس‌زدن wire format خودداری کند.


## 7. تطبیق با مشاهده runtime پاسخ هنگام بستن سند (2026-11-12)

در یک نشست واقعی Firefox، کاربر هنگام بستن نامه قابل ویرایش این رفتار را گزارش کرد:

- درخواست POST به endpoint محلی `127.0.0.1:1984` با `invoke=5208` و `Content-Type: text/plain;charset=UTF-8` مشاهده شد.
- با تغییر متن و فشردن Ctrl+S درخواست تازه‌ای به این endpoint مشاهده نشد.
- هنگام بستن Word، POST با همان مقدار گزارش‌شده invoke و HTTP status برابر 200 ثبت شد.
- ابتدای Response شامل XML declaration، ریشه `emwat version="1.0"`، متد `EditWordDocument` و پارامتر `wordConfig` بود.
- کاربر تگ‌های `Status`، `ErrorCode`، `Returntypes` یا `Error` را در ادامه قابل تشخیص پیدا نکرد؛ بدنه کامل پاسخ و انتهای XML هنوز در اختیار تحلیل نیست.

### تفسیر محدود

این مشاهده وجود پاسخ XML برای EditWordDocument در زمان بستن سند را runtime-validated می‌کند و با مدل ایستای Wordresponsexml (شامل Status، ErrorCode و Returntypes) قابل تطبیق است؛ اما ثابت نمی‌کند که XML مشاهده‌شده همان serialization کامل Wordresponsexml است. ممکن است wordConfig پارامتر پاسخ یا payload سند باشد و بخش‌های دیگر در ادامه یا در یک لایه دیگر قرار داشته باشند. همچنین HTTP 200 به‌تنهایی موفقیت ذخیره نهایی را اثبات نمی‌کند.

### اقدام بعدی برای تحلیل باینری

- callerهای `GetResponseWord`، `LoadResponseWord` و `NewResponseWord` را به متد `TEditWordDocument.PerformMethod` و dispatcher عمومی متصل کن.
- مشخص کن کدام تابع XML پاسخ را serialize می‌کند و چه زمانی `wordConfig` در response قرار می‌گیرد.
- eventهای `WordAppDocumentBeforeClose`، `SilentSaveEmwatDoc` و `OnTmrAutoSave` را از نظر ترتیب فراخوانی و فراخوانی‌های شبکه/connector تطبیق بده.
- تا پیش از اثبات این مسیرها، schema پاسخ یا معنای invoke=5208 را hard-code نکن.


## 8. مشاهده runtime نمونه word-document در حالت edit (2026-11-12)

کاربر مقدار Base64 داخل `wordConfig` در Response مربوط به چرخه بستن سند را به‌صورت محلی decode کرد و فقط ساختار XML را برای تحلیل ارائه داد. مقادیر واقعی اشخاص، نامه و سازمان در این مستند ثبت نمی‌شوند.

### ساختار مشاهده‌شده

ریشه سند:

```xml
<word-document status="edit">
```

مجوزها:

```xml
<permission allowPrint="false" allowCopy="true" allowSave="true"/>
```

بخش‌های سطح بالا در نمونه:

- `settings` با setting به نام `gam-print-dialog` و مقدار `false`.
- `fields` شامل metadata نامه، فرستنده/تولیدکننده، گیرندگان، امضاکنندگان و تصاویر.
- `optional-attributes` شامل attribute با شناسه `tokenizedReceivers` و نوع `compInfo`؛ محتوای آن URL-encoded است.
- `requested-types` شامل MIME type برابر `application/msword`.

### یافته‌های جدید درباره fieldها

- در نمونه واقعی، fieldهای متنی بدون ویژگی encoding نیز دیده شدند و مقدارشان در CDATA قرار داشت.
- برخی fieldهای متنی با `encryption="urlencoded"` مشخص شده‌اند؛ از جمله `RelatedLetters`، `LetterSubject` و فیلدهای گیرندگان.
- fieldهای تصویری با `encryption="base64"` و `mimetype="image/*"` تعریف شده‌اند؛ نمونه‌های شناخته‌شده شامل امضای فرستنده، امضای امضاکنندگان، QR code و barcode هستند.
- نام فیلدها خانواده‌های مشخصی را نشان می‌دهند: `LetterProducer*`، `LetterSender*`، `Receivers/ReceiverDeps`، `LetterSignerPer0..19`، `LetterSignerDep0..19`، `LetterSignerUnit0..19` و فیلدهای تصویری امضا.
- در همین نمونه، 20 slot برای metadata امضاکننده (اندیس 0 تا 19) تعریف شده‌اند. این موضوع ظرفیت schema را نشان می‌دهد، نه تعداد امضاکنندگان فعال هر نامه.
- فیلدهای خالی نیز به‌صورت self-closing یا بدون CDATA وجود دارند؛ parser و adapter باید نبود مقدار را بدون خطا بپذیرند.

### نکته مهم: Body در نمونه decodeشده دیده نشد

با وجود اینکه RTTI مدل `Wordrequestxml.TXMLWorddocumentType` propertyای به نام `Body` و type جداگانه `TXMLBodyType` را نشان می‌دهد، در نمونه XML decodeشده‌ای که کاربر ارائه کرد، عنصر `<body>` وجود نداشت. این مشاهده فقط به همین نمونه مربوط است؛ نمی‌توان نتیجه گرفت بدنه نامه در همه درخواست‌ها/پاسخ‌ها حذف می‌شود یا از مسیر دیگری می‌آید.

این تفاوت یک سرنخ مهم برای ادامه است: باید نمونه‌های request و response را در سطح ساختار (بدون مقدارها) مقایسه کنیم و در کد باینری مشخص کنیم چه زمانی Body مقداردهی می‌شود، آیا اختیاری است، و `LoadDocument/PrepareDocument` از چه منبعی محتوای اصلی Word را می‌سازند.

### تفسیر MIME type

نمونه `requested-types` مقدار `application/msword` را اعلام می‌کند. این یک MIME type درخواستی/مذاکره‌شده در مدل پروتکل است؛ به‌تنهایی ثابت نمی‌کند فایل برگشتی حتماً باینری DOC قدیمی است یا اینکه LibreOffice باید فقط DOC تولید کند. قالب واقعی فایل و مسیر تبادل آن هنوز باید از return typeها، فایل موقت یا بدنه پاسخ کامل تعیین شود.

### وضعیت اطمینان

- `status="edit"` و مجوزهای اعلام‌شده: مستقیماً در XML نمونه مشاهده شده‌اند.
- فیلدها و encodingهای بالا: مستقیماً از metadata XML نمونه مشاهده شده‌اند.
- نبودن `<body>` در همین نمونه: مستقیماً مشاهده شده است.
- منبع بدنه نامه، قالب واقعی فایل، و معنای دقیق `requested-types`: هنوز نامشخص.
- این XML شامل مقادیر واقعی مکاتبه بود؛ فقط schema و نام فیلدها ثبت می‌شود. هیچ مقدار شخصی، متن نامه، شناسه، Base64 تصویر یا token در مخزن نگهداری نمی‌شود.


## 9. بازبینی انتساب نمادها: Word viewer در برابر PrintHandler (2026-11-12)

گزارش تجمیعی رشته‌ها/نمادهای موجود در مخزن دوباره بررسی شد. این گزارش شامل نام نمادها و بخشی از RTTI است؛ بدنه اجرایی توابع یا ترتیب فراخوانی آن‌ها را ارائه نمی‌کند.

### نمادهای مستقل Wordviewer

نمادهای زیر در namespace مربوط به `Wordviewer` دیده می‌شوند:

- `Wordviewer.OpenDoc` با پارامتر `TEmwatInvokeParam`.
- `Wordviewer.TWordViwer.SilentSaveEmwatDoc`.
- `Wordviewer.TWordViwer.StoreFieldValuesForPrint`.
- `Wordviewer.TWordViwer.OnControlerNotify`.
- `Wordviewer.TEDPController.SetPrintThread` و `Notify`.

این موارد وجود یک کلاس/ماژول Word viewer و ارتباطی با controller/print thread را نشان می‌دهند. از روی نام‌ها به‌تنهایی نمی‌توان نتیجه گرفت که `SilentSaveEmwatDoc` حتماً هنگام BeforeClose اجرا می‌شود، چه فایلی را ذخیره می‌کند، یا نتیجه را چگونه به connector برمی‌گرداند.

### انتساب FillField به مسیر چاپ

نماد `FillField` در namespace متفاوتی قرار دارد:

```
Emwatdocprinthandlerunit.TEmwatDocPrintHandler.FillField
```

همان کلاس نمادهای دیگری مانند `PrepareDoc`، `Execute`، `CollectCustomField`، `GetDocFieldName` و متدهای تنظیم مقدار گیرندگان/CC را نیز دارد. بنابراین این `FillField` به‌طور مشخص متعلق به PrintHandler است و نباید آن را با helperهای احتمالی Word viewer برای پرکردن فیلدهای نامه یکی دانست. ممکن است هر دو مسیر از مفاهیم مشترک فیلد استفاده کنند، اما این اشتراک هنوز اثبات نشده است.

### RTTI مدل XML

گزارش نمادهایی برای `IXMLWorddocumentType.Get_Body`، `Get_Fields`، `Get_Status`، `Get_Permission`، `Get_Requestedtypes` و `Get_Optionalattributes` دارد. این شواهد وجود propertyهای مدل XML را تقویت می‌کند، ولی حضور عنصر `<body>` در هر پیام runtime را تضمین نمی‌کند؛ نمونه edit قبلی همچنان فقط در همان پیام فاقد آن عنصر بود.

### محدودیت منبع و تصمیم مهندسی

فایل تجمیعی `EMWAT-Analysis-Results.txt` نمادهای فوق را در بر دارد. در fetch فعلی، فایل مستقل `EmwatMethods.bpl1-strings.txt` محتوای قابل استفاده‌ای برنگرداند؛ بنابراین این مرحله بر گزارش تجمیعی تکیه دارد. هیچ disassembly تازه یا call graph معتبر در این مرحله به دست نیامد.

تصمیم فعلی برای پیاده‌سازی Linux:

1. قرارداد Word document و bridge از PrintHandler/print jobs جدا نگه داشته شود.
2. `FillField` متعلق به PrintHandler فقط در تحلیل/بازسازی مسیر چاپ استفاده شود.
3. برای lifecycle ویرایش، نقطه‌های شروع قابل پیگیری `OpenDoc` و `SilentSaveEmwatDoc` هستند؛ ترتیب و جزئیات آن‌ها تا بررسی بدنه کد نامشخص می‌ماند.
4. mapping آدرس‌ها باید ابتدا از PE sectionها و RVA به raw offset و سپس از TD32 segmentها به آدرس درست برسد؛ نام نماد به‌تنهایی مجوز حدس آدرس یا call order نیست.


## Run 99 — نخستین disassembly معتبر از Wordviewer و lifecycle (2026-11-12)

Artifact اجرای موفق GitHub Actions با SHA برابر `0eef619164c64f35afc2f4e075a82020f1ec7c70` بررسی شد. گزارش `EmwatMethods-target-disassembly.md` شامل 77 متد match‌شده است. متدهای زیر در ماژول 59 / segment 1 به PE section `.text` نگاشت شده‌اند؛ تفسیر segment-relative برای آن‌ها امتیاز plausibility بین 85 تا 90 دارد. این نگاشت نسبت به مراحل قبلی معتبرتر است، اما همچنان باید با داده‌های مستقل و callerها cross-check شود.

### متدهای قابل disassemble

| متد | VA | اندازه |
|---|---:|---:|
| `Wordviewer.OpenDoc` | `0x004B7430` | `0x2F4` |
| `TWordViwer.LoadDocument` | `0x004B7724` | `0x1360` |
| `TWordViwer.OnTmrAutoSave` | `0x004B8A84` | `0x292C` |
| `TWordViwer.OnControlerNotify` | `0x004BB3B0` | `0x3C8` |
| `TWordViwer.PrepareDocument` | `0x004BB77C` | `0xA0` |
| `TWordViwer.WordAppDocumentBeforeClose` | `0x004CCBBC` | `0x20C` |
| `TWordViwer.WordAppDocumentBeforeSave` | `0x004CD154` | `0x3F8` |
| `TWordViwer.SilentSaveEmwatDoc` | `0x004D23D8` | `0x444` |
| `TEDPController.Notify` | `0x004D2EC8` | `0x64` |

### شواهد جدید و تفسیر محدود

1. **ثبت handlerهای Word در مسیر timer:** در `OnTmrAutoSave`، کد pointerهای handler را روی object وابسته به Word viewer قرار می‌دهد. یکی از pointerها دقیقاً به entry متد `WordAppDocumentBeforeSave` یعنی `0x004CD154` اشاره می‌کند. چند callback دیگر نیز به `0x004D00AC`، `0x004CE030`، `0x004CD54C` و `0x004CD9C0` تنظیم می‌شوند. همچنین فراخوانی‌های virtual روی object مرتبط با Word انجام می‌شود. این شواهد وجود مکانیزم timer/event و اتصال BeforeSave را تأیید می‌کنند؛ اما به‌تنهایی ثابت نمی‌کنند که هر tick واقعاً سند را ذخیره یا به وب‌اپلیکیشن ارسال می‌کند.

2. **BeforeSave یک event handler واقعی است:** `WordAppDocumentBeforeSave` آرگومان سند را با reference داخلی مقایسه می‌کند، وضعیت‌های داخلی را بررسی می‌کند و در چند branch مقدار cancel را تنظیم می‌کند. در مسیرهای دیگر helperهای داخلی و یک فراخوانی virtual روی سند Word اجرا می‌شود. بنابراین برنامه در مسیر Save استاندارد Word مداخله می‌کند؛ اما از این بدنه به‌تنهایی نمی‌توان نتیجه گرفت که Ctrl+S همان payload شبکه‌ای را می‌سازد یا داده را به سامانه ارسال می‌کند.

3. **BeforeClose مسیر مستقل دارد:** `WordAppDocumentBeforeClose` event مربوط به بسته‌شدن را پردازش می‌کند و در نهایت به helper داخلی `0x004BCA88` می‌رسد. در همین بدنه فراخوانی مستقیم قابل‌شناسایی به `SilentSaveEmwatDoc` وجود ندارد. ممکن است helper یا dispatch غیرمستقیم به مسیر ذخیره متصل باشد، اما فعلاً اثبات نشده است.

4. **SilentSaveEmwatDoc بدنه اجرایی دارد:** متد `0x004D23D8` چند مجموعه/فیلد داخلی را از object دریافت می‌کند، برای بعضی مقادیر objectهای موقت می‌سازد، helper `0x004AEBBC` را فراخوانی می‌کند و flag داخلی در offset `+0x44C` را تنظیم می‌کند؛ سپس یک virtual call در offset `+0x13C` انجام می‌دهد. هیچ فراخوانی مستقیم با نام یا نماد Word COM Save در این بدنه دیده نشد. به‌دلیل نامشخص بودن نوع دقیق objectها و dispatchهای virtual، هنوز نمی‌توان گفت این متد فایل را کجا می‌نویسد یا چگونه payload را به bridge برمی‌گرداند.

5. **مسیر چاپ از مسیر ویرایش جدا می‌ماند:** `StoreFieldValuesForPrint` به `Base64Decode` و `SetForegroundWindowEX` می‌رسد و در گزارش helper graph نیز جدا از مسیر Save/Close قرار دارد. این متد را نباید به‌عنوان serializer عمومی سند ویرایش تلقی کرد.

6. **OpenDoc و LoadDocument اکنون بدنه قابل بررسی دارند، اما اتصال caller/callee هنوز کامل نیست:** هر دو متد با mapping قابل قبول disassemble شدند. helper graph هنوز فراخوانی مستقیم قابل‌انتساب بین آن‌ها را نشان نمی‌دهد؛ dispatchهای virtual و callbackها unresolved باقی مانده‌اند. بنابراین ترتیب قطعی اجرای آن‌ها فعلاً ثبت نمی‌شود.

### اثر بر طراحی Linux

- معماری باید eventهای `BeforeSave`، `BeforeClose` و timer/autosave را جداگانه مدل کند؛ ادغام آن‌ها در یک «ذخیره هنگام بستن» فرض تأییدنشده است.
- عملیات Save در LibreOffice باید با adapter مستقل پیاده شود و رفتار cancel/guardهای نسخه Windows بدون شناخت کامل آن‌ها کپی نشود.
- پاسخ HTTP 200 مشاهده‌شده در Firefox هنوز فقط شاهد پاسخ bridge هنگام close است؛ این disassembly رابطه قطعی آن پاسخ با `SilentSaveEmwatDoc` را اثبات نمی‌کند.
- گام بعدی تحلیل، استخراج callbackهای `0x4D00AC`، `0x4CE030`، `0x4CD54C` و `0x4CD9C0`، helper `0x4BCA88` و callerهای `OpenDoc` / `SilentSaveEmwatDoc` است؛ سپس باید dispatch virtual از طریق VMT/RTTI حل شود.

جزئیات assembly کامل در artifact CI نگهداری می‌شود؛ این سند فقط یافته‌های لازم را بدون داده محرمانهٔ نامه ثبت می‌کند.


## Run 100 — بررسی callerها و اصلاح تفسیر lifecycle (2026-11-12)

اجرای workflow با commit `44718f0` با موفقیت کامل شد: 147 مرحله از 147، بدون failure. Artifact جدید دریافت و فایل‌های callback/caller بررسی شدند.

### اصلاح مهم درباره SilentSaveEmwatDoc

تفسیر اولیه Run 99 بیش از حد به نام متد متکی بود. بدنه `TWordViwer.SilentSaveEmwatDoc` در `0x004D23D8` اکنون نشان می‌دهد که:

- به `Emwatutils.SetRegistryValue` مراجعه می‌کند.
- `TfrmWordPrintOption.SetLetterReceivers` را فراخوانی می‌کند.
- `TfrmWordPrintOption.FreePrinters` را فراخوانی می‌کند.
- `TWrapRecord.LineCount` را می‌خواند.
- چند property/collection را از object می‌خواند و از طریق virtual dispatch با آن‌ها کار می‌کند.

Caller مستقیم پیدا‌شده برای این متد، `TWordViwer.GetDocFieldName` در call site آدرس `0x004BBA86` است. در این caller، متد پس از یک شرط روی نتیجه قبلی فراخوانی می‌شود. هیچ caller مستقیم از `WordAppDocumentBeforeClose` یا `WordAppDocumentBeforeSave` در TD32 scan فعلی پیدا نشد.

**نتیجه اصلاح‌شده:** با وجود نام `SilentSaveEmwatDoc`، شواهد فعلی برای معرفی آن به‌عنوان serializer یا ذخیره‌کننده سند نامه کافی نیست؛ وابستگی‌های مستقیم قابل‌مشاهده‌اش بیشتر به تنظیمات چاپ/گیرندگان و رجیستری مربوط‌اند. تا زمان حل virtual dispatchها و بررسی داده‌های object، نقش دقیق آن باز می‌ماند. بنابراین آن را نباید به‌عنوان مسیر ذخیره نامه در پیاده‌سازی Linux بازسازی کرد.

### اصلاح مهم درباره helper آدرس 0x004BCA88

اسکن callerها نشان داد `0x004BCA88` فقط از `WordAppDocumentBeforeClose` فراخوانی نمی‌شود؛ دو call site دیگر نیز داخل `TWordViwer.GetCaptionItemFont` قرار دارند. بنابراین عنوان قبلی «helper مربوط به BeforeClose» دقیق نبود. این آدرس فعلاً یک helper مشترک با نقش نامشخص است و نباید به‌عنوان save/close routine تفسیر شود.

### یافته‌های دیگر caller scan

- برای `Wordviewer.OpenDoc` در محدوده procedureهای TD32 هیچ direct CALL xref پیدا نشد. این موضوع direct call از طریق کد خارج از محدوده، callback، یا VMT را رد نمی‌کند.
- برای `TWordViwer.LoadDocument` یک direct caller با نام `TScanDocument.PerformMethod` در `0x005EE961` پیدا شد. بنابراین این متد ممکن است در مسیر scan/document نیز استفاده شود و فعلاً نباید آن را منحصراً به بازشدن نامه متنی در Word نسبت داد.
- callbackهای ثبت‌شده در `OnTmrAutoSave` بدنه اجرایی دارند، اما در disassembly محدودشده فعلی هنوز نام/نقش معنایی قطعی آن‌ها مشخص نیست. در چند مورد کد از interface/virtual dispatch استفاده می‌کند؛ مقصد نهایی آن‌ها هنوز حل نشده است.

### تصمیم مهندسی به‌روزشده

1. نام `SilentSaveEmwatDoc` به‌تنهایی برای استنتاج ذخیره سند کافی نیست؛ این متد از مسیر بازسازی save-letter فعلاً کنار گذاشته می‌شود.
2. مسیرهای `BeforeSave` و `BeforeClose` جدا نگه داشته می‌شوند و از این disassembly نمی‌توان نتیجه گرفت که کدام‌یک باعث POST پاسخ‌دار مشاهده‌شده در Firefox شده است.
3. گام بعدی: disassemble کردن `TWordViwer.GetDocFieldName` و بررسی call chain آن، حل VMT/interface slotهای callbackهای timer، و پیدا کردن callerهای غیرمستقیم `OpenDoc`. سپس باید رفتار واقعی را با trace قابل‌اعتماد از یک نامه قابل ویرایش تطبیق داد.


## Run 101 — уточнение Word callbacks и вспомогательных методов (2026-11-12)

Источник: Artifact `emwat-bpl-static-analysis`, workflow run `43217998439`, commit `2e10d632508afcf6fd3792e49da7c08fc5f1c0fb`. CI завершился успешно; disassembly включает `TWordViwer.GetDocFieldName` и `TWordViwer.GetCaptionItemFont`.

### `GetDocFieldName` и `SilentSaveEmwatDoc`

- `TWordViwer.GetDocFieldName` сопоставлен с VA `0x004BB81C` (segment-relative mapping, score 87.5; PE section `.text`).
- Внутри метода видны обращения к коллекции/массиву по смещению объекта `+0xA4`, перебор элементов и вызовы вспомогательных методов/виртуальных интерфейсов. В частности, есть вызовы `0x004C0550`, `0x004D3F24`, `0x004D4528`, `0x004D45CC`, а также `0x004D281C`.
- Внутри этого метода действительно есть вызов `0x004D23D8` (`SilentSaveEmwatDoc`) по адресу `0x004BBA86`. Это подтверждает caller, но само по себе не меняет смысл метода: он находится внутри процедуры получения/обработки имени поля, а не в обработчиках BeforeClose/BeforeSave.
- Следовательно, имя `SilentSaveEmwatDoc` нельзя трактовать как доказательство сериализации тела письма или отправки его в Almas Gam. Его назначение по-прежнему не установлено; прежнее описание о взаимодействии с настройками печати/получателями/registry остаётся предварительным наблюдением по прямым вызовам.

### `GetCaptionItemFont` и общий helper `0x004BCA88`

- `TWordViwer.GetCaptionItemFont` сопоставлен с VA `0x004C19C0` (segment-relative mapping, score 87.5; PE section `.text`).
- Метод принимает `TCaptionItem`, `TDirection` и дополнительный параметр; его тело содержит работу с caption/font-параметрами и вызовы интерфейсных методов.
- Внутри него есть вызовы `0x004BCA88` (в частности, `0x004C2329`). Также этот адрес встречается в пути BeforeClose, поэтому helper общий и не может считаться специализированным обработчиком закрытия Word.
- Внутри `GetCaptionItemFont` видны вызовы `IG_ext_load` и `IG_ext_unload` из `GEAR32PD.DLL`; это связывает метод с ImageGear/обработкой caption-элементов, а не с сериализацией текста письма.
- Роль `0x004BCA88` остаётся неразрешённой до анализа его параметров, возвращаемого значения и всех callers.

### Вывод и следующий анализ

Новый артефакт уточняет два ложных направления: `GetCaptionItemFont` — часть caption/ImageGear-пути; `0x004BCA88` — общий helper. `SilentSaveEmwatDoc` вызывается из `GetDocFieldName`, но это не доказывает передачу отредактированного документа в браузер. Для доказательства жизненного цикла текста письма нужно продолжить трассировку вызовов `GetDocFieldName`, `0x004BCA88`, Word callbacks и фактической сериализации/ответного XML, не выводя назначение из имён.


## Run 102 — تفکیک helperهای Word و مسیر XML field (2026-11-12)

منبع: Artifact اجرای موفق `43219502021` (commit `7f053320c64512c61201737a2bdaa86bcae9bf47`).

### اصلاح callerهای `GetCaptionItemFont` و `0x004BCA88`

- اسکن callerها نشان می‌دهد `GetCaptionItemFont` مستقیماً از `AddImagesToDoc` در `0x004C048C` فراخوانی می‌شود؛ نه اینکه فعلاً بتوان آن را مسیر مستقل ذخیره/ویرایش متن دانست.
- helper `0x004BCA88` سه callsite مستقیم در محدوده متدهای TD32 دارد: دو بار از `GetCaptionItemFont` و یک بار از `WordAppDocumentBeforeClose`. بنابراین helper بین مسیر caption و رویداد بستن Word مشترک است؛ نقش دقیق و معنای مقدار Boolean بازگشتی هنوز مشخص نیست.
- `GetCaptionItemFont` در بدنه‌اش مسیرهای بارگذاری/آزادسازی افزونه‌های ImageGear را دارد. در کنار caller آن، این متد به پردازش caption/image در سند مربوط است؛ نه شواهدی برای انتقال متن نامه.

### نقش جدید helper `0x004BC980`

- caller scan، `0x004BC980` را در `GetXmlFieldInfo`، `GetDocFieldIndex` و `FillImgFldsForPrint` نشان می‌دهد.
- در `GetXmlFieldInfo` چهار بار و در `GetDocFieldIndex` سه بار فراخوانی می‌شود؛ در `FillImgFldsForPrint` دو callsite دارد.
- بدنه helper با interface/virtual calls در offset `+0xB0` کار می‌کند، مقادیر بازگشتی را بررسی می‌کند و در مسیر نامعتبر به helper استثنا/خطا `0x004BC30C` می‌رسد. در چند caller ثابت `0x004BF9A0` به آن داده می‌شود.
- این شواهد آن را به مسیر دسترسی/اعتبارسنجی اطلاعات XML field و fieldهای تصویری چاپ مرتبط می‌کند؛ اما نوع دقیق interface و قرارداد ورودی/خروجی هنوز از روی این disassembly به تنهایی اثبات نشده است.
- caller scan برای `GetDocFieldName` و `GetCaptionItemFont` به ترتیب صفر و یک caller مستقیم نشان می‌دهد. این نتیجه فقط درباره CALL مستقیم در محدوده متدهای TD32 است و dispatch مجازی/غیرمستقیم را پوشش نمی‌دهد.

### گام بعدی

برای جدا کردن مسیر اصلی متن از مسیر تصویر، متدهای `GetXmlFieldInfo`، `GetDocFieldIndex`، `AddImagesToDoc` و `FillImgFldsForPrint` به targetهای disassembly اضافه شدند. تحلیل بعدی باید قرارداد field lookup، تشخیص mimetype/encryption و نقطه‌ای را پیدا کند که مقدار فیلدهای ویرایش‌شده از Word خوانده یا به XML پاسخ تبدیل می‌شود. هنوز هیچ‌کدام از این یافته‌ها به تنهایی اثبات ذخیره نهایی نامه نیست.


## Run 103 — بررسی lookup فیلدهای XML و مسیر افزودن تصاویر (2026-11-12)

منبع: workflow run `43220472439`، commit `2007fa954217512724830b161cac52772c44ef12`؛ CI با نتیجه موفق، 147/147 مرحله. Artifact شماره `13946301787` دریافت و بررسی شد.

### `GetXmlFieldInfo`

- overload دارای خروجی `TXmlWordConfigField` در VA `0x004BFC18` نگاشت شده است (segment-relative، score حدود 88.8، بخش PE برابر `.text`).
- این تابع ابتدا index را به مقدار `-1` و flag خروجی را false می‌گذارد؛ سپس دو مجموعه/collection داخلی در offsetهای `+0x68` و `+0x6C` را بررسی می‌کند.
- در مسیر اول، با نام ورودی lookup انجام می‌دهد و در صورت یافتن، index و یک مقدار متنی/مشخصه از رکورد را برمی‌گرداند. در مسیر دوم نیز lookup جایگزین انجام می‌دهد و در بعضی حالت‌ها دو رشته را با هم مقایسه می‌کند؛ در صورت تطبیق، index و مشخصه‌های رکورد را خروجی می‌دهد و flag را true می‌کند.
- بنابراین این overload به‌طور مستقیم منطق جست‌وجو و resolve کردن metadata فیلدهای XML را نشان می‌دهد. معنای دقیق دو collection و فیلدهای خروجی هنوز از روی این تابع به‌تنهایی قطعی نیست.
- overload دیگر `GetXmlFieldInfo` در `0x004BCA88` بسیار بزرگ‌تر است و از helper `0x004BC980` برای دسترسی به interface/XML field استفاده می‌کند؛ این آدرس با helper قبلی Run 102 هم‌پوشانی دارد و باید با احتیاط از overload کوچک‌تر تفکیک شود.

### `AddImagesToDoc` و caption

- `AddImagesToDoc` در VA `0x004C0410` (score حدود 88.8) دریافت‌کننده `Wordxp.Fields` و interface مربوط به XML field است.
- تابع از interface یک مقدار/رشته می‌خواند، آن را با یک ثابت داخلی مقایسه می‌کند و در صورت عبور از شرط، `GetCaptionItemFont` را در `0x004C048C` صدا می‌زند. این با caller scan قبلی Run 102 سازگار است.
- این مسیر شواهد مستقیم از پردازش field/caption در زمان افزودن تصاویر به سند Word می‌دهد؛ اما به‌تنهایی نه serializer متن نامه است و نه مسیر ارسال پاسخ به مرورگر.

### مواردی که هنوز از artifact به دست نیامد

- در فایل target-disassembly این اجرا، procedure مستقلی با نام‌های `GetDocFieldIndex` یا `FillImgFldsForPrint` match نشده است؛ بنابراین جزئیات callerهای گزارش‌شده در Run 102 هنوز با disassembly بدنه این دو متد تکمیل نشد.
- هیچ نقطه‌ای در این اجرا ثابت نمی‌کند که Body نامه از Word خوانده و در پاسخ HTTP/XML قرار داده می‌شود. همچنین درباره اینکه بستن Word باعث ذخیره نهایی در Almas Gam می‌شود، نتیجه جدیدی حاصل نشد.

### نتیجه و ادامه

اکنون یک قطعه روشن‌تر از معماری داریم: EMWAT برای resolve کردن نام/metadata فیلدهای XML دو collection داخلی را جست‌وجو می‌کند و مسیر افزودن تصاویر به Word از interface فیلدها به منطق caption می‌رسد. گام بعدی باید به‌جای گسترش تصادفی targetها، روی بدنه و callerهای واقعی `GetXmlFieldInfo`، callbackهای Word و ساخت `Wordresponsexml`/ `Returntypes` متمرکز شود تا محل استخراج مقدارهای تغییرکرده و تولید پاسخ مشخص شود.


## تکمیل schema پاسخ Word از RTTI — مسیر response مستقل از payload (2026-11-12)

در گزارش نمادها/RTTI مخزن (EMWAT-Analysis-Results.txt) چند interface مربوط به XML پاسخ Word و سند قابل‌ویرایش دیده می‌شود. این‌ها شواهد schema هستند، نه هنوز شواهدی از نقطه اجرای serializer:

- IXMLResponseWordType دارای propertyهای Status، ErrorCode و Returntypes است.
- IXMLReturntypesType دارای property Type است؛ نوع MIME/فرمت خروجی احتمالاً در همین سطح مدل می‌شود، اما مقادیر واقعی و نحوه تولید آن هنوز از کد اجرایی استخراج نشده است.
- IXMLGlobalResponseType نیز Status و ErrorCode دارد؛ نباید این مدل global را بدون بررسی به response اختصاصی Word یکی دانست.
- IXMLWorddocumentType دارای Body، Fields، Status، Settings، Permission، Requestedtypes و Optionalattributes است.
- IXMLBodyType حداقل property مربوط به Encryption را در RTTI دارد. محتوای Body و قرارداد دقیق رمزگذاری آن هنوز از این نمادها به‌تنهایی معلوم نیست.

### ارتباط با trace مرورگر

در نمونه قابل ویرایش کاربر، XML داخلی word-document دارای status=edit بود و عنصر body در همان نمونه دیده نشد. وجود getter مربوط به Body در interface نشان می‌دهد Body بخشی از مدل XML/قرارداد نوعی است، اما نبود آن در نمونه خاص می‌تواند به optional بودن، خالی بودن یا مسیر متفاوت payload مربوط باشد؛ هیچ‌یک هنوز اثبات نشده‌اند.

همچنین گزارش کاربر که در Response مشاهده‌شده Status، ErrorCode و Returntypes را پیدا نکرده، لزوماً با RTTI تناقض ندارد: ممکن است این propertyها در مدل response جداگانه باشند و Response فعلی صرفاً envelope حاوی wordConfig باشد. برای تعیین این موضوع باید implementation و callerهای response XML بررسی شوند.

### محدودیت و گام بعد

نام interface و getter/setter فقط ساختار نوعی را ثابت می‌کنند. هنوز معلوم نیست کدام تابع این مدل را instantiate می‌کند، چه زمانی Body را مقدار می‌دهد، آیا متن Word به‌صورت plain text یا فایل/stream برمی‌گردد و Returntypes در کدام پاسخ واقعی ظاهر می‌شود. ادامه تحلیل باید ابتدا symbol/procedureهای همین interfaceها و سپس callerهای TEditWordDocument.PerformMethod و ParamsToXML را به هم متصل کند.


## Run 103 — XML field lookup and image insertion path (2026-11-12)

CI run 43222525062 completed successfully (147/147 steps; no failed steps). Artifact: emwat-bpl-static-analysis, id 13947156509.

### New confirmed method mappings

- TD32 maps an overload of TWordViwer.GetXmlFieldInfo to VA 0x004BFC18 (size 0x11D; high mapping score). The method initializes an output index to -1 and a Boolean output to false, checks two field collections reachable through object offsets +0x68 and +0x6C, compares requested strings against field metadata through helper calls, and when a match is found returns the field index plus a string value/attribute. This is direct evidence of XML field metadata lookup; it is not a document-body serializer.
- A second GetXmlFieldInfo overload is mapped at 0x004BCA88 (TD32 procedure size 0x3190). It calls helper 0x004BC980 repeatedly with the constant at 0x004BF9A0 and uses several XML-interface vtable methods to traverse/read collections. The earlier generic label “shared helper 0x4BCA88” should be treated as superseded: TD32 names this address as a GetXmlFieldInfo overload. Its callers from GetCaptionItemFont and WordAppDocumentBeforeClose are therefore consistent with metadata lookup being reused in image/caption and close handling, not proof that this address is a generic save helper.
- AddImagesToDoc maps to 0x004C0410 (size 0x140). It obtains a field identifier through an XML interface getter, compares it with a constant string, and for the non-matching branch delegates to GetCaptionItemFont at 0x004C19C0 with the Word Fields object, field/index arguments and XML field interface. This confirms a hand-off from image-field processing into the caption/font path. The short method itself does not establish the full image byte-transfer or save/return protocol.
- TEmwatMethod.Invoke maps to 0x0046C82C (size 0x1B1). It traverses a generic dictionary/enumerator-like structure using virtual interface calls and helper routines. This is consistent with parameter/dictionary processing, but the disassembly does not identify the HTTP response serializer or prove that it serializes the Word document body.
- ParamsToXML at 0x0046AD10 is only a 5-byte jump thunk to 0x00401068. The actual implementation is therefore not in the emitted procedure body; the next analysis must resolve the jump target and its callers before attributing XML serialization behavior to it.

### What Run 103 does not prove

- No TEditWordDocument.PerformMethod body was selected from this BPL's TD32 target set. The class/method may live in another module or be represented by a thunk/indirect dispatch; this run does not resolve that.
- GetXmlFieldInfo and AddImagesToDoc operate on field metadata/image-caption paths. They do not establish how edited document text is extracted from Word, whether it is placed in word-document/Body, how returned MIME data is built, or what close/Save actually transmits.
- The previously observed editable XML sample lacking a <body> element remains a single-sample observation. RTTI still establishes Body in the schema, but no runtime population path has been found.

### Next analysis target

Resolve 0x00401068 (ParamsToXML thunk destination), inspect all direct/indirect callers of ParamsToXML and TEmwatMethod.Invoke, and identify the module containing TEditWordDocument.PerformMethod. In parallel, trace the Word COM close/save callbacks toward any routine that reads document content or constructs the response dictionary/return types.


## بررسی مقصد thunk مربوط به ParamsToXML — 2026-11-12

- بدنه `ParamsToXML` در `0x0046AD10` یک jump پنج‌بایتی به `0x00401068` است؛ بنابراین آن آدرس بدنه اختصاصی serializer نیست، بلکه یک thunk/واسط پرش به Import Address Table است.
- disassembly موجود از ناحیه `.text` نشان می‌دهد `0x00401068` دستور `jmp dword ptr [0x0062EE24]` دارد. این فقط ثابت می‌کند مقصد نهایی از slot مربوط به IAT resolve می‌شود؛ تا زمانی که import متناظر با slot `0x0062EE24` از PE استخراج نشود، نام تابع و معنای آن معلوم نیست.
- بنابراین نام `ParamsToXML` به‌تنهایی برای نتیجه‌گیری اینکه این متد XML پاسخ نامه را serialize می‌کند کافی نیست. حتی اگر مقصد یک تابع عمومی RTL باشد، باید callerها و داده‌های ورودی/خروجی بررسی شوند تا نقش واقعی روشن شود.
- Commit مربوط به افزودن trace هدف به workflow در `d4577ce` ثبت شده، اما در زمان این بررسی Actions هنوز اجرای جدیدی برای آن commit نشان نمی‌داد؛ پس هیچ نتیجه CI تازه‌ای برای این trace ادعا نمی‌شود.

### گام بعدی

1. استخراج دقیق import متناظر با IAT slot `0x0062EE24` و ثبت نام DLL/symbol.
2. caller scan برای `ParamsToXML` و بررسی اینکه خروجی آن کجا مصرف می‌شود.
3. یافتن ماژول/بسته‌ای که `TEditWordDocument.PerformMethod` در آن پیاده‌سازی شده؛ نبودن بدنه آن در TD32 این BPL به معنی نبودن آن در کل برنامه نیست.
4. ادامه ردیابی callbackهای Word تا routineای که محتوای تغییرکرده سند را می‌خواند یا response model را می‌سازد.


## Run 104 — بررسی IAT و callerهای مستقیم ParamsToXML (2026-11-12)

Artifact اجرای موفق workflow با run ID برابر `43226336477` بررسی شد؛ هر 148 مرحله CI بدون failure پایان یافت.

### نتایج

- آدرس IAT بررسی‌شده `0x0062EE24` دقیقاً به import با نام `rtl230.bpl!@System@@AbstractError$qqrv` resolve شد. این فقط هویت همان slot را مشخص می‌کند و هیچ ارتباط اثبات‌شده‌ای با serializer نامه یا `ParamsToXML` ندارد.
- برای entry مربوط به `ParamsToXML` در `0x0046AD10` هیچ direct CALL reference در executable sectionهای همین PE پیدا نشد.
- برای `TEmwatMethod.Invoke` در `0x0046C82C` نیز direct CALL reference پیدا نشد.
- یادآوری: نبود direct CALL، فراخوانی از طریق VMT/interface، callback، jump محاسبه‌شده یا caller خارج از این PE را رد نمی‌کند.

### تصمیم و گام بعدی

در Run 103 مشخص شده بود که `ParamsToXML` در `0x0046AD10` فقط یک jump thunk پنج‌بایتی به `0x00401068` است. بنابراین Run 104 به‌تنهایی مقصد اجرایی آن را بررسی نکرده و هنوز درباره serializer نتیجه‌ای نمی‌دهد. Workflow اکنون برای اجرای بعدی، disassembly و thunk trace آدرس `0x00401068` را جداگانه تولید می‌کند و direct caller scan را نیز به این مقصد گسترش می‌دهد. این کار در commit `2b440ed3ebe1e6b3d1a144941cefe43a5cf70ad9` ثبت شده است.

تا قبل از بررسی خروجی جدید، نقش `ParamsToXML` و مسیر serialization/بازگشت سند نامشخص باقی می‌ماند.


## Run 105 — مقصد ظاهری ParamsToXML به import thunk ختم می‌شود (2026-11-13)

Artifact اجرای workflow با run ID برابر `43232846364` با موفقیت کامل بررسی شد (148/148 مرحله).

### یافته قطعی در محدوده فایل بررسی‌شده

- رکورد TD32 برای `ParamsToXML` یک procedure پنج‌بایتی در segment 48/1 با offset برابر `0x69D10` دارد. candidate مبتنی بر segment-relative آن در VA `0x0046AD10` فقط یک دستور است: `jmp 0x00401068`؛ این candidate از فیلتر کیفیت disassembly عبور نکرده است.
- آدرس مقصد `0x00401068` در PE به‌عنوان یک import thunk disassemble می‌شود: `jmp dword ptr [0x0062EE24]`.
- جدول import، slot برابر `0x0062EE24` را به `rtl230.bpl!@System@@AbstractError$qqrv` resolve می‌کند.
- بنابراین trace این candidate به یک thunk وارداتی برای routine خطای RTL ختم می‌شود، نه به بدنه‌ای که بتوان آن را serializer XML دانست. اسکن direct CALL نیز برای `0x0046AD10`، `0x00401068` و `TEmwatMethod.Invoke` در `0x0046C82C` caller مستقیم پیدا نکرد.

### تفسیر اصلاح‌شده

این نتیجه **اثبات نمی‌کند** که پیاده‌سازی واقعی `ParamsToXML` همان `AbstractError` است. برعکس، چون candidate پنج‌بایتی unresolved است و به یک import thunk خطا ختم می‌شود، انتساب آدرس `0x0046AD10` به بدنه واقعی `ParamsToXML` قابل اتکا نیست؛ احتمال دارد رکورد TD32 به stub/alias یا mapping نامعتبر در این BPL اشاره کند و implementation در package/module دیگری باشد. باید محل تعریف/resolve شدن symbol در packageهای Delphi و relocation/import metadata بررسی شود.

### تصمیم و گام بعدی

- `ParamsToXML` فعلاً از فهرست توابعی که بدنه اجرایی‌شان در این BPL پیدا شده خارج می‌شود.
- نباید از این trace نتیجه گرفت که XML با `AbstractError` ساخته می‌شود یا serialization شکست می‌خورد.
- گام بعدی، بررسی package/import metadata برای نماد `ParamsToXML`، بررسی BPLهای وابسته و cross-check کردن سایر procedureهای پنج‌بایتی unresolved است تا مشخص شود این یک الگوی package forwarding است یا mapping اشتباه.
- هیچ تغییری در قرارداد Linux یا طراحی save/return بر اساس این trace انجام نمی‌شود؛ مسیر serialization همچنان حل‌نشده است.


## Run 105 — شناسایی stub متد ParamsToXML و بررسی dispatch کلاس‌ها (2026-11-13)

در artifact اجرای موفق run `43232846364` (148/148 مرحله) رکورد کامل TD32 برای نماد زیر دیده شد:

`@Emwatmethod@ParamsToXML$qqrx20System@UnicodeStringxp76System@Generics@Collections@%TDictionary__2$27System@%AnsiStringT$us$i0$%t1%`

این رکورد در module 48 / segment 1 با offset برابر `0x69D10` و اندازه 5 بایت قرار دارد. candidate فعلی آن در `0x0046AD10` دستور `jmp 0x00401068` است؛ مقصد `0x00401068` نیز `jmp dword ptr [0x0062EE24]` بوده و slot وارداتی به `rtl230.bpl!@System@@AbstractError$qqrv` resolve می‌شود.

این الگو با stub متد abstract در Delphi سازگار است؛ بنابراین محتمل است `TEmwatMethod.ParamsToXML` در کلاس پایه abstract باشد و implementation موردنیاز از طریق override/VMT یا package دیگر resolve شود. با این حال، این فقط یک تفسیر قوی از الگوی stub است: رابطه override و مقصد runtime هنوز از روی VMT تأیید نشده است. همچنین آدرس `0x0046AD10` نباید به‌عنوان بدنه واقعی serializer استفاده شود.

در همان artifact، نماد `@Wordviewer@TWordViwer@GetXmlFieldInfo` در `0x004BFC18` یک متد مجزا در module 59 است؛ شباهت موضوعی آن به XML field lookup هیچ دلیلی برای یکسان دانستن آن با `ParamsToXML` نیست.

### ابزارهای پیگیری اضافه‌شده

- `tools/search_td32_word_methods.py` برای فهرست‌کردن نمادهای TD32 مرتبط با `ParamsToXML`، `PerformMethod`، `TEmwatMethod`، `TEditWordDocument` و وابستگی‌های package.
- `tools/resolve_delphi_vmt_slots.py` اکنون VMT کلاس‌های `TEmwatMethod` و `TEditWordDocument` را نیز بررسی می‌کند و slotهای بیشتری را dump می‌کند.
- Workflow این گزارش‌ها را در artifact بعدی تولید می‌کند. commitهای ابزار/Workflow: `a3f57c0`, `ab080e8`, `df3f91e`.

گام بعدی: بررسی اینکه VMT کلاس پایه کدام slot را به stub abstract متصل می‌کند، آیا کلاس فرزند override واقعی دارد، و آیا مقصد آن در همین BPL یا package دیگری قرار دارد. تا آن زمان serialization و save/return سند همچنان حل‌نشده است.


## 10. تفکیک callbackهای چاپ از lifecycle ثبت هنگام بستن سند (2026-11-13)

Disassembly تکمیلی نشان داد callbackهای `0x004CE030` و `0x004D00AC` به رویداد `Document.OnBeforePrint` مربوط‌اند. helperهای downstream آن‌ها شامل `0x004CF5B4`، `0x004CF748`، `0x004CFC74`، `0x004CF158` و `0x004AEBBC` هستند و عمدتاً context/مقادیر داخلی چاپ را بین interfaceها و اشیای مقصد جابه‌جا می‌کنند. این مسیرها از callback واقعی `WordAppDocumentBeforeClose` در `0x004CCBBC` جدا هستند.

در callback بستن سند، دو فراخوانی مجازی با VMT offset برابر `+0x38` دیده می‌شود و سپس `GetXmlFieldInfo` در `0x004BCA88` فراخوانی می‌شود. این callback به‌تنهایی در trace فعلی POST یا serialization پاسخ `EditWordDocument` را نشان نمی‌دهد.

همچنین تابع `0x004CD9C0` سه رشته محلی را به dispatch مجازی `+0x29C` می‌دهد؛ داده UTF-16 نزدیک آن شامل پیام **«دسترسی به این بخش میسر نیست»** و عبارت **«اموتا - Gam Document»** است. این یک سرنخ برای بررسی مسیر permission/error یا پیام UI است، نه مدرک ارسال سند.

### مسیر بررسی بعدی

Workflow جدید، بدنه `GetXmlFieldInfo`، `OnTmrAutoSave`، `OnControlerNotify`، `OpenDoc` و `LoadDocument` را trace می‌کند. هدف اتصال مشاهده runtime زیر به dispatcher واقعی است:

- POST به `127.0.0.1:1984` هنگام بستن سند
- `invoke=5208`
- پاسخ XML با متد `EditWordDocument` و پارامتر `wordConfig`

تا وقتی caller و ترتیب eventها مشخص نشده‌اند، نباید `BeforeClose`، `OnTmrAutoSave` یا `OnControlerNotify` را به‌تنهایی مسئول ارسال پاسخ معرفی کرد.


## 11. یافته جدید درباره ثبت callbackهای Word (Run 107)

Disassembly تابع `TWordViwer.OnTmrAutoSave` در `0x004B8A84` نشان می‌دهد این تابع callbackهای رویداد Word را روی شیء/ساختار وابسته به document ثبت می‌کند:

- `+0x80` ← `WordAppDocumentBeforeSave` در `0x004CD154`
- `+0x90` ← `0x004CD54C`
- `+0x98` ← `0x004CD9C0`
- `+0x88` ← یکی از دو callback چاپ `0x004D00AC` یا `0x004CE030`، بسته به وضعیت byte در `[this+0x3C]`

بنابراین نام `OnTmrAutoSave` به‌تنهایی توصیف کامل نقش این تابع نیست؛ شواهد مستقیم نشان می‌دهند که wiring چند event handler را هم انجام می‌دهد. هنوز معلوم نیست کدام callback یا کدام dispatch در نهایت باعث POST مشاهده‌شده هنگام close می‌شود.

تابع `OnControlerNotify` در `0x004BB3B0` وضعیت‌هایی را بررسی می‌کند، flagهای موقتی `+0x79` و `+0x5E` را تغییر می‌دهد، helper `0x004D281C` را فراخوانی می‌کند و سپس یک متد interface با offset `+0xDC` را روی شیء `+0x48` اجرا می‌کند. در trace فعلی ارسال مستقیم HTTP/XML دیده نشده است.

تابع `GetXmlFieldInfo` در `0x004BCA88` مجموعه‌ای از interfaceها و propertyها را پیمایش می‌کند و helper `0x004BC170` را برای تطبیق/پردازش مقادیر فراخوانی می‌کند. شواهد فعلی با استخراج metadata فیلدهای XML سازگارند؛ اما trace 320 دستور هنوز کامل نیست.

گام بعدی، trace کامل‌تر این دو تابع و helperهای controller است تا wiring رویدادها به مسیر `EditWordDocument` و پاسخ `wordConfig` متصل شود.


## Deep lifecycle trace update (2026-11-13)

The expanded trace artifact from workflow run `43500518664` completed successfully (artifact `14073787351`). It adds the following static evidence:

- `OnTmrAutoSave` at `0x004B8A84` registers a callback record on the object referenced by `[this+0x44]`. The record stores the document context and function pointers: `+0x80 -> 0x004CD154` (BeforeSave), `+0x90 -> 0x004CD54C`, `+0x98 -> 0x004CD9C0`, and `+0x88 -> 0x004D00AC` or `0x004CE030` depending on `[this+0x3C]`. The function later repeats the BeforePrint callback selection and invokes additional interface methods at offsets `+0x100` and `+0x108`. This is event/callback wiring and document-state handling; it is not, by itself, proof of the HTTP request or payload serialization.
- `OnControlerNotify` reaches `0x004D281C`, which TD32 identifies as `TWordViwer.CostumizeRecAndCC`. The method uses `TWordViwer+0x48` (the current `Wordxp._Document` interface), toggles the state byte at `+0x5C`, and invokes `_Document.PrintOutOld()` three times through slot `+0x2BC`. This is a COM interface dispatch, not an unresolved internal Delphi VMT slot.
- The extended `GetXmlFieldInfo` trace (`0x004BCA88`) traverses multiple interfaces/collections and repeatedly invokes interface methods while building field-related values. The 1800-instruction capture ends mid-function; do not treat it as a complete function listing or as evidence of network transfer.
- The helper at `0x004CDB54` checks a value obtained from `[this+0x44]` against a string constant and returns a Boolean. The helper at `0x004C5D68` reads two properties through interface calls and stores Boolean/state bytes at `[this+0x4C]` and `[this+0x4D]`. Neither helper contains a direct HTTP/serialization call in the captured body.

### Next static-analysis target

The earlier Delphi VMT resolver remains useful for internal class diagnostics, but it is not the table used by this Word callback path. The current `TWordViwer+0x48` field is a `Wordxp._Document` COM interface, and slot `+0x2BC` maps to `PrintOutOld()`. The remaining close-path investigation now focuses on the separate `WordAppDocumentBeforeClose -> +0x38 interface dispatches -> GetXmlFieldInfo` path. Runtime-confirmed behavior remains separate: closing the Word document causes the local bridge request `invoke=5208` with an `EditWordDocument` XML payload containing `wordConfig`; the static callback-to-HTTP chain is not yet proven end-to-end.


## Run 108 — deep trace رویدادهای Word و dispatch کنترلر (2026-11-14)

Artifact اجرای موفق run `43500518664` با شناسه `14073787351` بررسی شد.

### جزئیات تکمیلی OnTmrAutoSave

در تابع `TWordViwer.OnTmrAutoSave` در `0x004B8A84`، پس از ثبت callbackهای Word، مسیر زیر نیز دیده می‌شود:

- helper `0x004CDB54` مقداری را که از شیء `[this+0x44]` به دست می‌آورد با ثابت رشته‌ای مقایسه می‌کند و نتیجه Boolean برمی‌گرداند. معنای business رشته هنوز مشخص نیست.
- در شاخه شرطی دیگر، مسیر نمایش/ثبت پیام و فراخوانی `0x00441C68) و interface method با offsetهای `+0x54`، `+0x100` و `+0x108` دیده می‌شود.
- helper `0x004C5D68` دو property را از interface شیء `[this+0x44]` می‌خواند: dispatchهای مجازی با offsetهای `+0x15C` و `+0x104`. نتایج در byteهای `[this+0x4C]` و `[this+0x4D]` ذخیره می‌شوند.
- انتخاب callback چاپ `0x004D00AC` یا `0x004CE030` در مسیر دوم نیز تکرار می‌شود.

این یافته‌ها نقش تابع را به‌عنوان setup و هماهنگ‌کننده event/state تقویت می‌کنند؛ اما در trace هیچ فراخوانی مستقیم HTTP، ساخت XML پاسخ یا ارسال payload دیده نشده است. به‌دلیل dispatchهای interface، پیاده‌سازی واقعی propertyها هنوز باید از VMT/RTTI resolve شود.

### جزئیات تکمیلی OnControlerNotify و helper کنترلر

تابع `OnControlerNotify` در `0x004BB3B0`:

- property/stateای را از `[this+0x7C]` می‌خواند و فقط در صورت غیرصفر بودن `[this+0x58]` وارد شاخه اصلی می‌شود.
- از interface شیء `[this+0x44]` مقدارهایی را با dispatch `+0xE0` می‌گیرد؛ یکی از مقادیر عددی را با `0x14` مقایسه می‌کند و اگر مقدار از 20 بیشتر نباشد از آن شاخه خارج می‌شود.
- در شاخه عبوری، byteهای `[this+0x79]` و `[this+0x5E]` را موقتاً تغییر می‌دهد، helper `0x004D281C` را صدا می‌زند و سپس interface method با offset `+0xDC` را روی شیء `[this+0x48]` اجرا می‌کند.

خود helper `0x004D281C` byte وضعیت `[this+0x5C]` را فعال می‌کند، متد مجازی با offset بایتی `+0x2BC` را روی شیء `[this+0x48]` اجرا می‌کند و سپس flag را پاک می‌کند. همین dispatch در مسیر exception نیز تکرار می‌شود. بنابراین `+0x2BC` مهم‌ترین نقطه فعلی برای resolve کردن implementation واقعی controller/document notification است.

### محدودیت trace و تصمیم مرحله بعد

- trace تابع `GetXmlFieldInfo` در `0x004BCA88` با سقف 1800 دستور، در میانه بدنه متوقف شده است؛ این capture بدنه کامل تابع نیست.
- trace خطی تابع `OnTmrAutoSave` نیز در ناحیه‌ای شامل داده/بخش‌های exception به انتهای disassembly معتبر نرسیده است؛ بنابراین پایان واقعی تابع و همه branchها هنوز استخراج نشده‌اند.
- توابع helper `0x00440950`، `0x00440A68` و `0x00441C68` wrapperهای کوتاه برای فراخوانی interface method در offsetهای `+0x174`، `+0x180` و `+0x1E0` هستند؛ معنای دقیق این slotها بدون resolve کردن interface/VMT مشخص نیست.

گام بعدی باید مسیر جداگانهٔ BeforeClose را دنبال کند: دو dispatch از slot `+0x38` در `WordAppDocumentBeforeClose` و سپس فراخوانی `GetXmlFieldInfo`. برای این کار scan جدید تمام callsiteهای `+0x38` را با wrapperهای WordXP مقایسه می‌کند. مشاهده runtime درخواست `invoke=5208` هنگام بستن سند همچنان جدا از زنجیرهٔ ایستای هنوز حل‌نشده ثبت می‌شود.


## Run 109 — ارزیابی خروجی VMT و اصلاح فیلتر مقصدها (2026-11-14)

اجرای workflow شماره 9 با شناسه `43502841837` موفق شد و artifact آن با شناسه `14075266227` بررسی شد. نتیجه مهم این مرحله، محدودیت ابزار VMT فعلی بود:

- در خروجی کلاس `TEDPController`، متد `Notify` در slot `+0x6C` به آدرس معتبر `0x004D2EC8` نگاشت شده است.
- در خروجی `TWordViwer`، slot `+0x2A4` به `AddXmlWordConfigFieldsToDic` در `0x004D1148` نگاشت شده است.
- در خروجی `TEmwatDocPrintHandler`، slot `+0x2A4` به `GetDocFieldName` در `0x004A8F78` نگاشت شده است.
- هیچ‌یک از مقادیر گزارش‌شده برای slot `+0x2BC` در این سه کلاس به یک محدوده procedure معتبر TD32 نگاشت نشد. مقادیر اولیه‌ای که workflow قبلاً به‌عنوان candidate دنبال می‌کرد، صرفاً اعداد خام/آدرس‌های خارج از section بودند و trace آن‌ها بی‌اعتبار است.

بنابراین هنوز implementation متد virtual فراخوانی‌شده از `[this+0x48]` در `OnControlerNotify` مشخص نشده است. از این پس workflow فقط مقصدهایی را trace می‌کند که resolver آن‌ها را صریحاً داخل محدوده یک TD32 procedure شناخته باشد؛ این اصلاح جلوی تبدیل مقادیر خام VMT به آدرس تابع فرضی را می‌گیرد.

نکته: موفقیت GitHub Actions در این مرحله فقط موفقیت اجرای ابزار تحلیل است، نه اثبات حل‌شدن dispatch یا پروتکل. برای حل slot `+0x2BC` باید ساختار VMT/RTTI و نحوه تشخیص مرز virtual method table در resolver دقیق‌تر شود؛ احتمال دارد VMTهای این کلاس‌ها به‌علت چیدمان metadata یا inheritance به اسکن اختصاصی‌تری نیاز داشته باشند.


## Run 110 — بررسی section و بایت‌های اطراف candidateهای VMT (2026-11-14)

Workflow شماره 11 با run ID برابر `43504757084` و commit برابر `a4328e191dcff8f5e8a96660a127b67e21419d04` با موفقیت کامل شد. artifact شماره `14074289309` شامل گزارش تازه `Word-VMT-slots.md` و بایت‌های خام اطراف candidateهاست.

### یافته‌های مستقیم

سه candidate مورد بررسی در PE section با نام `.text` قرار دارند و section دارای مجوز execute/read است؛ فیلد class-name pointer گزارش‌شده برای هر سه نیز در همین section قرار گرفته است:

| کلاس | candidate | class-name pointer | داده قابل توجه |
|---|---:|---:|---|
| `TWordViwer` | `0x004B10A4` | `0x004B106C` | self-pointer برابر candidate و instance size برابر `0x11C`؛ در بایت‌های ابتدای candidate مقادیر `0x0E`، `0x00100000` و چند مقدار نامعتبر به‌عنوان pointer دیده می‌شود. |
| `TEDPController` | `0x004B0DFC` | `0x004B0DC4` | self-pointer برابر candidate و instance size برابر `0x24`؛ ناحیه پس از candidate شامل رشته RTTI مانند `OnNotify`، `PrintThread` و نام کلاس است؛ slot گزارش‌شده `+0x6C` به `TEDPController.Notify` در `0x004D2EC8` می‌رسد. |
| `TEmwatDocPrintHandler` | `0x004A22F0` | `0x004A22B8` | self-pointer برابر candidate و instance size برابر `0xE4`؛ ابتدای ناحیه چند pointer اجرایی معتبر دارد، اما در ادامه داده‌های غیرقابل‌تفسیر به‌عنوان slot تابع ظاهر می‌شوند؛ slot `+0x2A4` به `GetDocFieldName` در `0x004A8F78` resolve شده است. |

### تفسیر و محدودیت

- قرار گرفتن candidate در `.text` به‌تنهایی دلیل رد آن نیست؛ برخی linkerها/ساختارهای PE می‌توانند داده‌های read-only را در همان section کد قرار دهند. بنابراین نباید صرفاً بر اساس نام یا permission section فیلتر قطعی اعمال شود.
- در عین حال، تطبیق self-pointer، instance size و parent pointer نیز به‌تنهایی برای اثبات مرز VMT کافی نیست. بایت‌های اطراف candidateها نشان می‌دهند که بخشی از ناحیه شامل RTTI/method metadata و مقادیر غیر pointer است؛ اسکن فعلی ممکن است مرز VMT، جدول متدهای RTTI و slotهای مجازی را با هم اشتباه بگیرد.
- وجود یک مقصد TD32 معتبر در یک offset (مانند `TEDPController +0x6C` یا `TEmwatDocPrintHandler +0x2A4`) فقط معتبر بودن آن مقصد به‌عنوان procedure را نشان می‌دهد؛ به‌تنهایی ثابت نمی‌کند offset نسبت به base فعلی، slot مجازی همان کلاس است.
- برای `TWordViwer`، `TEDPController` و `TEmwatDocPrintHandler` هنوز مقصد معتبر و تأییدشده‌ای برای `+0x2BC` به دست نیامده است. بنابراین اتصال dispatch در `0x004D281C` به یک implementation مشخص همچنان حل‌نشده است.

### گام بعدی

Resolver باید به‌جای اتکا به یک base فرضی، ساختار Delphi VMT را با توجه به layout دقیق نسخه کامپایلر و RTTI جداگانه بازسازی کند: مرز VMT، method table، dynamic method table، interface table و extended RTTI باید تفکیک شوند. سپس slotهای مجازی با توالی pointerهای اجرایی و cross-referenceهای constructor/class reference اعتبارسنجی شوند. تا قبل از آن، هیچ مقصدی برای `+0x2BC` hard-code نمی‌شود و هیچ نتیجه‌ای درباره ارسال HTTP از این VMT report گرفته نمی‌شود.

## Run 19–21 — شناسایی رابط COM سند Word در dispatch آفست +0x2BC (2026-11-14)

نتیجهٔ جدید، تفسیر قبلی VMT را دقیق‌تر می‌کند: نبودن مقصد معتبر در candidateهای VMT داخلی EMWAT همچنان درست است، اما اکنون شواهد قوی داریم که dispatch موردنظر در مسیر Word از رابط COM نوع `Wordxp._Document` عبور می‌کند، نه از VMT کلاس داخلی `TWordViwer`.

- امضای TD32 برای `TWordViwer.WordAppNewDocument` و `TWordViwer.WordAppDocumentBeforeSave` شامل `DelphiInterface<Wordxp._Document>` است.
- فیلد `TWordViwer+0x48` با پارامتر ورودی `_Document` مقایسه می‌شود و سپس همان reference در callbackهای Word استفاده می‌شود.
- `WordAppNewDocument` روی reference سند، فراخوانی indirect از offset `+0x2BC` در `0x004CD6BF` انجام می‌دهد.
- `OnControlerNotify` نیز از helper در `0x004D281C` استفاده می‌کند که همان فیلد `+0x48` را خوانده و از offset `+0x2BC` dispatch می‌کند.
- `OnTmrAutoSave` آدرس `0x004CD54C` را در event record در offset `+0x90` ثبت می‌کند؛ TD32 این procedure را `WordAppNewDocument` نام‌گذاری می‌کند. بنابراین نبودن direct CALL-xref برای این callback طبیعی است.
- اسکن کامل‌تر 28 reference برای displacement `+0x2BC` پیدا کرد؛ این عدد در interfaceهای مختلف Word/Excel و چند بخش دیگر هم دیده می‌شود. بنابراین فقط callsiteهایی که receiver آن‌ها با نوع `_Document` اثبات شده باشد برای تعیین method موردنظر قابل استفاده‌اند.

گزارش کامل شواهد و محدودیت‌ها: [`WORD-COM-INTERFACE-DISPATCH.md`](WORD-COM-INTERFACE-DISPATCH.md).

نام متد در slot شماره 175 (`0x2BC / 4`) برای interface نوع `_Document` اکنون با اطمینان بالا `PrintOutOld()` است. این یافته به‌تنهایی مسیر HTTP محلی، `invoke=5208` یا XML پاسخ `EditWordDocument` را اثبات نمی‌کند؛ گام بعدی بررسی dispatchهای جداگانهٔ `+0x38` در callback بستن سند است.

## Run 132 — نگاشت slot مربوط به Word `_Document` به PrintOutOld (2026-11-14)

تحلیل wrapperهای WordXP نام متد را با اطمینان بالا مشخص کرد:

- procedure با نام `Wordxp.TWordDocument.PrintOutOld` در `0x004309F8`، بدون آرگومان، interface داخلی سند را از helper `0x0042ABA0` دریافت می‌کند و سپس از vtable آن در offset `+0x2BC` فراخوانی انجام می‌دهد (`0x00430A1E`).
- overload دارای یک آرگومان در `0x00430A4C` از `+0x2C0` استفاده می‌کند و overloadهای بعدی به ترتیب از `+0x2C4` و offsetهای بعدی استفاده می‌کنند.
- بنابراین slot `+0x2BC` در `Wordxp._Document` با اطمینان بالا متد بدون آرگومان `PrintOutOld()` است.
- در مقابل، wrapper `Wordxp.TWordApplication.ToggleKeyboard` نیز از عدد `+0x2BC` روی interface نوع `_Application` استفاده می‌کند؛ نام متد به نوع interface وابسته است و نباید offset خام را به‌تنهایی تفسیر کرد.

در نتیجه، فراخوانی `TWordViwer.WordAppNewDocument` در `0x004CD6BF` و dispatch مسیر `OnControlerNotify -> 0x004D281C` روی فیلد `_Document`، به احتمال بسیار بالا `Wordxp._Document.PrintOutOld()` را اجرا می‌کنند؛ نه Save یا Close. دلیل اجرای عملیات چاپ در این callback هنوز روشن نیست و باید شرط‌های قبل و بعد از dispatch بررسی شوند.

جزئیات و شواهد disassembly: [`WORD-COM-INTERFACE-DISPATCH.md`](WORD-COM-INTERFACE-DISPATCH.md).

توجه: فراخوانی‌های هم-offset در `CloseMyDoc` و `UnprotectMyDoc` هنوز به interface مشخصی منتسب نشده‌اند؛ تا زمان اثبات نوع receiver نباید آن‌ها را هم `PrintOutOld` فرض کرد.

### تکمیل Run 133 — CostumizeRecAndCC

تحلیل TD32 آدرس `0x004D281C` را به‌طور قطعی به `TWordViwer.CostumizeRecAndCC` نسبت داد. این متد سه بار از فیلد `TWordViwer+0x48` استفاده می‌کند و در هر سه مورد slot `+0x2BC` را صدا می‌زند. با نگاشت wrapper در Run 132، هر سه فراخوانی به `Wordxp._Document.PrintOutOld()` بدون آرگومان مربوط می‌شوند. متد فلگ `TWordViwer+0x5C` را هنگام اجرا فعال و در خروج پاک می‌کند.

بنابراین مسیر `OnControlerNotify -> CostumizeRecAndCC` اکنون از نظر نام متد و نوع عملیات COM روشن شده است: فراخوانی PrintOutOld است، نه Save یا Close. دلیل کاربرد سه‌بارهٔ آن در منطق Rec/CC هنوز نیازمند بررسی است و این مسیر به‌تنهایی درخواست HTTP محلی را ثابت نمی‌کند.

### شرط اجرای CostumizeRecAndCC در OnControlerNotify

ردیابی کامل `TWordViwer.OnControlerNotify` نشان می‌دهد فراخوانی `CostumizeRecAndCC` شرطی است: ابتدا از interface ذخیره‌شده در `TWordViwer+0x44` مقدار رویداد خوانده می‌شود؛ مقدار پس از تبدیل با `0x14` مقایسه می‌شود و فقط اگر بزرگ‌تر باشد، helper اجرا می‌شود. پس از آن slot `+0xDC` روی interface جاری `_Document` در `TWordViwer+0x48` فراخوانی می‌شود. معنای تجاری event code هنوز مشخص نیست و نباید این مسیر را با close event یا POST محلی یکی دانست.

### Run 22 — بررسی slot +0x38 در WordAppDocumentBeforeClose

اسکن package-wide تعداد 462 reference برای displacement `+0x38` پیدا کرد. دو callsite مربوط به `WordAppDocumentBeforeClose` (`0x004CCC2C` و `0x004CCCB2`) به‌تنهایی برای تعیین نام متد کافی نیستند؛ همین offset در wrapperهای مختلف WordXP برای interfaceهای متفاوت استفاده می‌شود. نمونه‌ها شامل `TWordDocument.Get_Tables`، `TWordFont.Get_Hidden`، `TWordParagraphFormat.Get_KeepTogether`، `TWordOLEControl.Get_Name` و `TWordApplication.Get_Selection` هستند. خود `GetXmlFieldInfo` نیز `+0x38` را روی interfaceهای `Wordconfigrequestxml.IXMLFieldType` فراخوانی می‌کند.

پس نوع receiver در BeforeClose هنوز باید از dataflow و event-record source تعیین شود. برای مقایسه، بدنهٔ wrapper `TWordDocument.Get_Tables` در تحلیل BPL بعدی اضافه شده است.


## Static lifecycle trace extension — field-list nested helper (2026-11-14)

Lifecycle runs 27–30 expanded the trace around the TD32 symbol `TWordViwer.WordAppDocumentBeforeClose` at `0x004CCBBC`.

The complete caller trace shows that `0x004CCBBC` is directly called from `FillImgFldsForPrint` at `0x004CCF8F`. The call passes the caller's EBP as a Delphi nested-procedure static link. The target's receiver expression `[[ebp+8]-0x0C]` therefore resolves to the parent `FillImgFldsForPrint` local that captured incoming ECX.

The only direct TD32-bounded caller found for `FillImgFldsForPrint` is `TWordViwer.GetFieldIndexInList` at `0x004CB361`. That method calls `TWordViwer.FillPrintDocFields` at `0x004CB638`; the latter's TD32 signature explicitly declares an input `DelphiInterface<Wordxp._Document>` and an output `DynamicArray<DelphiInterface<Wordxp.Fields>>`. `GetFieldIndexInList` iterates this array and passes each `Wordxp.Fields` interface element in ECX to `FillImgFldsForPrint`. The latter and its nested helper dispatch through the `Wordxp.Fields` interface vtable at slots `+0x28` and `+0x38`.

**Interpretation boundary:** the receiver type is now statically identified as `Wordxp.Fields`, not merely an interface-like pointer and not `_Document`. The exact method names at slots `+0x28` and `+0x38` remain to be mapped. The target is clearly a nested helper reached in a print/field-list path; its TD32 symbol name alone is not proof that it is independently registered as a Word close event. Do not identify its `+0x38` calls as `_Document.Get_Tables()`; that mapping applies only to the separate typed `Wordxp.TWordDocument.Get_Tables` wrapper.

No direct link has yet been established from this helper body to the observed localhost POST `127.0.0.1:1984/?invoke=5208` or the `EditWordDocument/wordConfig` XML response. The user-observed behavior that closing the document applies changes even without pressing Save remains a confirmed product requirement; this static trace has not yet identified the internal event or transport implementing it.

See [WORD-COM-INTERFACE-DISPATCH.md](WORD-COM-INTERFACE-DISPATCH.md) for instruction-level details and the run-31 follow-up targets.


### Run 31 follow-up: typed Word Fields receiver

The full TD32 signature for `TWordViwer.FillPrintDocFields` at `0x004CB638` resolves the list element type. It accepts `Wordxp._Document` and produces `DynamicArray<DelphiInterface<Wordxp.Fields>>`. `GetFieldIndexInList` then iterates that array and passes each `Wordxp.Fields` element to `FillImgFldsForPrint`; the nested `0x004CCBBC` helper receives the same interface through its static link.

The next step is now narrow and type-directed: enumerate the Word wrapper VMT/RTTI for `TWordFields`, `TWordField`, and `TWordDocument`, map `Wordxp.Fields` slots `+0x28` and `+0x38`, and independently find the actual close-event registration and invoke/response path.


### Run 33 — WordXP interface GUIDها و عملیات collection

اسکن RTTI رابط‌ها در artifact شماره 33 این IIDها را از خود BPL استخراج کرد:
- `Wordxp.Fields`: `00020930-0000-0000-C000-000000000046`
- `Wordxp.Field`: `0002092F-0000-0000-C000-000000000046`
- `Wordxp._Document`: `0002096B-0000-0000-C000-000000000046`
- `Wordxp.Tables`: `0002094D-0000-0000-C000-000000000046`

GUIDهای `Fields` و `Field` با هویت interfaceهای Word در مستندات Microsoft Learn تطبیق دارند. در مسیر بررسی‌شده، slot `+0x28` روی `Wordxp.Fields` با الگوی getter تعداد و مصرف مقدار به‌عنوان loop bound، به‌احتمال بسیار زیاد `Fields.Count` است. slot `+0x38` با دریافت index و خروجی interface، به‌احتمال بسیار زیاد `Fields.Item(index)` است که یک `Wordxp.Field` برمی‌گرداند. این نام‌گذاری‌ها inference با اطمینان بالا هستند؛ نوع receiver و IID از RTTI اثبات شده‌اند، اما declaration کامل vtable هنوز استخراج نشده است.

Run 33 همچنین تنها caller مستقیم TD32-bounded برای `GetFieldIndexInList` را در `TWordViwer.BGPrintWithGamPrintOptions` در `0x004C6F3F` یافت. بنابراین زنجیرهٔ `BGPrintWithGamPrintOptions → GetFieldIndexInList → FillPrintDocFields → Wordxp.Fields → FillImgFldsForPrint → nested helper` در مسیر پردازش فیلدهای چاپ قرار دارد. این یافته نام TD32 تابع `WordAppDocumentBeforeClose` را به‌تنهایی برای اثبات ثبت آن به‌عنوان event واقعی Close ناکافی می‌کند.

منابع عمومی تطبیق IID و معنای collection: [Microsoft Learn — Fields](https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.fields?view=word-pia)، [Microsoft Learn — Field](https://learn.microsoft.com/en-us/dotnet/api/microsoft.office.interop.word.field?view=word-pia).


### Run 41 — typed Fields getter and unresolved alternate document dispatch

The complete TD32 body for `Wordxp.TWordDocument.Get_Fields` at `0x0042B55C` calls the common `TWordDocument` interface accessor `0x0042ABA0`, then dispatches `+0x80` on the returned interface. The direct-call scan found no immediate CALL xrefs to this wrapper.

This provides a typed getter positive control, but it also exposes an important distinction: `TWordViwer.FillPrintDocFields` calls `+0x12C` on its typed `Wordxp._Document` input with multiple output arguments. That call must **not** be labelled `Get_Fields` based only on the fact that the procedure eventually produces `DynamicArray<Wordxp.Fields>`. Its method identity and intermediate interface types remain unresolved. The next scan adds `Range`, `_Range`, and `StoryRanges` RTTI candidates to help type the intermediate COM interfaces.


### Run 44 — بررسی pointerهای ثبت callback در کل PE

اسکن exact pointerهای ۳۲بیتی در تمام sectionهای PE برای routine با آدرس `0x004CCBBC` هیچ referenceای پیدا نکرد. در مقابل، آدرس‌های callbackهای شناخته‌شده در routine `OnTmrAutoSave` در `.text` پیدا شدند و بدنهٔ همان routine انتساب method pointerها به زوج فیلدهای event object را نشان می‌دهد: BeforeSave=`0x004CD154` در زوج `+0x80/+0x84`، NewDocument=`0x004CD54C` در `+0x90/+0x94`، handler دیگر=`0x004CD9C0` در `+0x98/+0x9C` و BeforePrint=`0x004CE030` یا `0x004D00AC` در `+0x88/+0x8C`.

این شواهد، ثبت ایستای `0x004CCBBC` به‌عنوان BeforeClose را در همین BPL بسیار نامحتمل می‌کند؛ اما absence of exact pointer به‌تنهایی ثبت محاسبه‌شده، registration در package دیگر یا مسیر runtime دیگر را رد نمی‌کند. از آنجا که `0x004CCBBC` به‌صورت قطعی از مسیر print/field صدا زده می‌شود، نام TD32 آن نباید به‌عنوان اثبات callback واقعی Close استفاده شود. مسیر POST هنگام بستن سند هنوز باید از event/connector دیگری ردیابی شود.


## Service-side dispatch is now statically traced (2026-11-14)

The service-side half of the observed close request is no longer an unknown black box. The extracted `EmwatService.exe` proves:

`POST body → TEmwatInvokeParam.BufferIn → XML parser (0x00470B38) → method@class + param nodes → GetClass("T"+className) → TEmwatMethod base dispatch (VMT +0x0C) → subclass PerformMethod (VMT +0x10)`.

For the observed runtime envelope `EditWordDocument`, the class resolution is `TEditWordDocument`, and its concrete VMT slot `+0x10` target is `0x005EE82C`. This method reads the `document` parameter and calls helper `0x004B7724`. The helper is now included in the next lifecycle trace.

**What remains unproven:** which Word/COM callback or browser-side event handler emits the `postMessage` that causes the close-time POST. The service parser/dispatcher path is established, but this does not by itself prove the upstream event source or the final document commit/save semantics. The user's runtime observation that closing applies the changes remains the behavioral requirement.

Also note the corrected ID distinction: browser query `invoke=<random>` is not the service's `TEmwatInvokeParam.SessionId`; the service generates a separate six-digit internal SessionId.


### Run 77 — TEditWordDocument parameters and HTTP response path

The concrete VMT target `TEditWordDocument.PerformMethod` at `0x005EE82C` retrieves four named request parameters:

- `wordConfig`
- `wordBody`
- `letterImages`
- `signData`

It starts a worker thread, logs `CoInitializing thread`, and passes those four values plus the `TEmwatInvokeParam*` request context and an output-string reference to helper `0x004B7724`.

After the helper returns, `TEditWordDocument` copies the returned string into the base dispatcher's output string and sets `bUnloadPkg=true). It leaves `bResultSet=false). The generic service dispatcher therefore takes its default response branch: it assigns the returned string to `AResponseInfo.ContentText`, sends the HTTP response via `0x004610FC`, and sets `bResultSet=true`.

This is a concrete link between the observed runtime `EditWordDocument` response and the service's XML method dispatcher. The output string is produced downstream of `0x004B7724`; that helper is now the key target for identifying Word automation, document update and response XML construction. The method's four parameter names are statically proven, but their runtime values/encoding and the exact commit operation still need tracing.
