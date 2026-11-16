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

1. **ثبت handlerهای Word در مسیر timer:** در OnTmrAutoSave، کد pointerهای handler را روی object وابسته به Word viewer قرار می‌دهد. طبق اصلاح runهای 25 و 26، آدرس 0x004CD154 در event record +0x80 قرار دارد اما TD32 آن را WordAppDocumentBeforeSave معرفی می‌کند، نه BeforeClose. آدرس‌های دیگر شامل 0x004CD54C در +0x90، 0x004CD9C0 در +0x98 و 0x004D00AC یا 0x004CE030 در +0x88 (BeforePrint) هستند. این شواهد وجود مکانیزم timer/event را تأیید می‌کنند؛ اما به‌تنهایی ثابت نمی‌کنند که هر tick سند را ذخیره یا به وب‌اپلیکیشن ارسال می‌کند.

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
- The inner dictionary/XML helper is at 0x0046C82C (size 0x1B1; TD32 symbol says TEmwatMethod.Invoke). The public virtual TEmwatMethod.Invoke wrapper is at 0x0046C9E0 (BPL export name; VMT slot +0x0C). The wrapper calls the helper, then dispatches subclass PerformMethod through VMT slot +0x10.
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

- `OnTmrAutoSave` at `0x004B8A84` registers a callback record on the object referenced by `[this+0x44]`. The corrected mapping from runs 25–26 is `+0x80 -> 0x004CD154` (TD32: BeforeSave), `+0x90 -> 0x004CD54C`, `+0x98 -> 0x004CD9C0` (NewDocument export/Activation handling), and `+0x88 -> 0x004D00AC` or `0x004CE030` depending on `[this+0x3C]` (BeforePrint). The earlier BeforeClose label for 0x004CD154 was wrong. This is callback wiring and document-state handling; it is not, by itself, proof of the HTTP request or payload serialization.
- `OnControlerNotify` reaches `0x004D281C`, which TD32 identifies as `TWordViwer.CostumizeRecAndCC`. The method uses `TWordViwer+0x48` (the current `Wordxp._Document` interface), toggles the state byte at `+0x5C`, and invokes `_Document.PrintOutOld()` three times through slot `+0x2BC`. This is a COM interface dispatch, not an unresolved internal Delphi VMT slot.
- The extended `GetXmlFieldInfo` trace (`0x004BCA88`) traverses multiple interfaces/collections and repeatedly invokes interface methods while building field-related values. The 1800-instruction capture ends mid-function; do not treat it as a complete function listing or as evidence of network transfer.
- The helper at `0x004CDB54` checks a value obtained from `[this+0x44]` against a string constant and returns a Boolean. The helper at `0x004C5D68` reads two properties through interface calls and stores Boolean/state bytes at `[this+0x4C]` and `[this+0x4D]`. Neither helper contains a direct HTTP/serialization call in the captured body.

### Next static-analysis target

The earlier Delphi VMT resolver remains useful for internal class diagnostics, but it is not the table used by this Word callback path. The current TWordViwer+0x48 field is a Wordxp._Document COM interface, and slot +0x2BC maps to PrintOutOld(). The 0x004CCBBC -> +0x38 -> GetXmlFieldInfo path is a nested image-field helper reached from FillImgFldsForPrint, despite its TD32 WordAppDocumentBeforeClose label. The callback registered at event-record +0x80 is 0x004CD154, but runs 25–26 identify it as WordAppDocumentBeforeSave. It checks Saved, prompts, and invokes the document interface's +0x29C slot with three OleVariant arguments on Yes/No. Runtime-confirmed behavior remains separate: closing the Word document causes the local bridge request invoke=5208 with an EditWordDocument XML payload containing wordConfig; the parent-page message that initiates this request is not yet traced.


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

این مسیر `+0x38 → GetXmlFieldInfo` در آدرس `0x004CCBBC` در تحلیل run 26 به‌عنوان helper فیلدهای تصویر/چاپ با یک caller مستقیم (`FillImgFldsForPrint`) شناسایی شد؛ نقش آن به‌عنوان event واقعی Close اثبات نشده است. callback ثبت‌شده در `0x004CD154` در event record در offset `+0x80` قرار دارد، اما TD32 آن را `WordAppDocumentBeforeSave` معرفی می‌کند، نه BeforeClose. این callback وضعیت `Document.Saved` را از slot `+0xD8` می‌خواند، پیام Yes/No/Cancel نشان می‌دهد و در Yes/No مستقیماً slot `+0x29C` را با سه OleVariant صدا می‌زند. درخواست runtime `invoke=5208` همچنان باید از پیام parent-page به bridge تا POST دنبال شود.


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
- `OnTmrAutoSave` آدرس `0x004CD54C` را در event record در offset `+0x90` ثبت می‌کند. TD32 این procedure را `WordAppNewDocument` نام‌گذاری می‌کند، اما export table و رشته‌های داخل بدنه آن را `WordAppDocumentBeforeSave` معرفی می‌کنند؛ این اختلاف نام باید حفظ شود. نبودن direct CALL-xref برای این callback طبیعی است.
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

For the observed runtime envelope `EditWordDocument`, the class resolution is `TEditWordDocument`, and its concrete VMT slot `+0x10` target is `0x005EE82C`. This method reads `wordConfig`, `wordBody`, `letterImages`, and `signData`, then calls `TWordViwer.LoadDocument` at `0x004B7724` with the `TEmwatInvokeParam*` and output-string reference.

**Correction to earlier close-event progress:** `TWordViwer.OnTmrAutoSave` registers `0x004CD154` at event-record `+0x80`, but TD32 identifies that procedure as `WordAppDocumentBeforeSave`, not `WordAppDocumentBeforeClose`. It calls `PreparePrintDocument` (`0x004CB108`), checks `Document.Saved` through `_Document` slot `+0xD8`, prompts Yes/No/Cancel, sets the event Cancel word on Cancel, and directly invokes interface slot `+0x29C` with three OleVariant arguments on Yes/No. The separately named `WordAppDocumentBeforeClose` at `0x004CCBBC` has only a direct caller from `FillImgFldsForPrint` (`0x004CCF8F`) in the bounded scan and no raw-pointer registration reference; its active event role is unproven. Do not rely on the earlier callback label or claim a registered BeforeClose handler.

**What remains unproven:** the close callback body has no direct HTTP request call. The embedded browser bridge is now deobfuscated: it forwards parent `postMessage` event data unchanged to the local service via XHR and posts `responseText` back to the original source/origin. The remaining task is to identify which parent-page code sends the close-time message and how the final document content is committed. The user's observed apply-on-close behavior remains the behavioral requirement.

The browser's `invoke=<random>` value is generated only as a per-request URL nonce/cache-buster; it is not a method ID or service SessionId. The service independently generates a six-digit `TEmwatInvokeParam.SessionId`.


### Run 77 — concrete EditWordDocument input and response path

The concrete VMT target `TEditWordDocument.PerformMethod` at `0x005EE82C` retrieves four named request parameters from the parsed dictionary:

- `wordConfig`
- `wordBody`
- `letterImages`
- `signData`

It starts a worker thread, logs `CoInitializing thread`, and calls `TWordViwer.LoadDocument` at `0x004B7724`. The register/stack arguments prove the mapping:

| LoadDocument argument | Source |
|---|---|
| EAX | `wordConfig` |
| EDX | `wordBody` |
| ECX | `letterImages` |
| `[EBP+8]` | output-string reference |
| `[EBP+0x0C]` | `TEmwatInvokeParam*` |
| `[EBP+0x10]` | `signData` |

The helper parses `wordConfig` as XML and checks the `word-document` root. It writes the `wordBody` bytes into a stream, stores `signData` in Wordviewer state (field `+0xF4`), and processes the configuration/image path. Its strings and branches include `image/tif`, `Payam-e-Dowlat` handling, and a `view` mode. It also logs `ConfigXML data loaded.`, `Word doc content added to result.`, and `OpenDoc function succeed.`. The document output is read from a temporary file with retry handling (the loop limit is 100 attempts) and the temporary file is subsequently deleted.

During this path, `LoadDocument` calls `TWordViwer.OnTmrAutoSave` at `0x004B8A84` with the viewer instance and configuration string. That routine stores/parses the configuration and registers Word automation callbacks, including:

- `+0x80 → 0x004CD154` (TD32: `WordAppDocumentBeforeSave`; corrected by runs 25–26)
- `+0x90 → 0x004CD54C`
- `+0x98 → 0x004CD9C0` (NewDocument export; body includes Activation/Quitword handling)
- `+0x88 → 0x004D00AC` or `0x004CE030` depending on viewer state (BeforePrint paths)

Do not interpret 0x004CD154 as BeforeClose. The separately named TD32 routine at 0x004CCBBC has only a direct bounded caller from FillImgFldsForPrint and no raw-pointer registration reference; its active event role is unproven.

**Correction to the earlier Run 77 response interpretation:** `TEditWordDocument` itself sets `bUnloadPkg=true` after `LoadDocument`, but `LoadDocument` can set `bResultSet=true` itself. On the non-empty-result path at `0x004B7F9C–0x004B7FBF`, it:
1. obtains `AResponseInfo` from `TEmwatInvokeParam.AResponseInfo` at record offset `+0x0C);
2. assigns the output XML string to `AResponseInfo.ContentText` at object offset `+0xBC);
3. calls imported `IdCustomHTTPServer.TIdHTTPResponseInfo.WriteContent` (thunk `0x0040448C`, IAT slot `0x0062F9C0`);
4. sets `TEmwatInvokeParam.bResultSet` at record offset `+0x05` to true.

Therefore the generic service dispatcher does **not** take its fallback response branch when this successful non-empty result path has already written the response. The output is an XML response containing the document result metadata/content (the helper references `application/msword` and `success`); the exact serialized element layout and encoding still need a byte-for-byte comparison with a captured runtime response.

This proves a concrete response path from `EditWordDocument` through Wordviewer document generation to Indy HTTP `WriteContent`. It does not yet identify the browser/Word event that initiates the close-time POST or prove the final apply-on-close semantics.


## Generic Invoke XML parameter serialization (BPL evidence, 2026-11-14)

The generic TEmwatMethod.Invoke path accepts a TDictionary<System.AnsiString,System.AnsiString> and constructs an XML object hierarchy through three interfaces:

1. A TXMLEmwatType interface is initialized in local [ebp-4].
2. Its interface slot +0xB0 creates a TXMLMethodType interface in [ebp-1C].
3. The TXMLMethodType interface slot +0xCC inserts a child TXMLParamType interface in [ebp-8].
4. For each dictionary pair, the TXMLParamType interface receives the first string through slot +0xB0 and the second string through slot +0x68.

The two parameter methods are now identified:
- TXMLParamType +0xB0 resolves through thunk 0x0044BDF5 to 0x0044C8E4. Its body calls xmlrtl230.bpl!TXMLNode.SetAttribute(UnicodeString, OleVariant) using the literal attribute name name and the first dictionary-pair member as the value.
- TXMLParamType +0x68 resolves through thunk 0x0044BEB5 to 0x0044B568, an IAT jump to xmlrtl230.bpl!TXMLNode.SetText(UnicodeString). The second dictionary-pair member becomes the parameter node's text.

Therefore each dictionary pair is serialized as an XML parameter node equivalent in structure to <param name="KEY">VALUE</param>. This is a static BPL-level serialization result. Do not yet assume it is byte-for-byte the same XML envelope observed in the browser's localhost POST/response; the TXMLMethodType +0xC8 dispatch receives the method-name string and resolves through thunk 0x0044BA59 to implementation target 0x0044C62C. Its TD32 label is TXMLMethodType.Get_Param, but its body calls TXMLNode.SetAttribute with the method-name string and a static attribute-name literal at 0x0044C6A4; that literal is being decoded and is expected to match the service parser's method@class field.

After the loop, the inner helper at 0x0046C82C calls the TXMLEmwatType interface at slot +0x54 (callsite 0x0046C937) with an output reference, then copies the returned XML string into its caller-provided output string through runtime helper 0x004012F8. This proves that the generic Invoke routine serializes the constructed XML tree to a string. The interface VTable slot is at 0x0044B8CC; its target method name is still to be mapped. The TXMLMethodType +0xC8 method-name setter is also still under investigation.

## Confirmed generic Invoke XML serialization (2026-11-14, focused runs 11 and 16)

The earlier Generic Invoke XML parameter serialization section above contains now-superseded pending statements about the class literal and serializer getter. Focused runs 11 (43571811038) and 16 (43573798242) resolve those points:

- TXMLMethodType.AfterConstruction (0x0044C458) initializes the method node using literal method.
- TXMLMethodType interface slot +0xC8 resolves to 0x0044C62C; this body calls TXMLNode.SetAttribute with literal class and the supplied method-name string.
- Each parameter child is a TXMLParamType; the dictionary key is assigned to attribute name, and the dictionary value becomes node text via TXMLNode.SetText.
- TXMLEmwatType interface slot +0x54 resolves through thunk 0x0044B7A9 to xmlrtl230.bpl!TXMLNode.GetXML (0x0044B590), which produces the serialized XML string returned by Invoke.

The proven tree shape is a method element with class equal to the dispatched method name and parameter child nodes with name attributes and text values. This is static BPL evidence. It does not yet establish exact serialization whitespace, XML declaration, encoding, any additional root attributes, or byte-for-byte equivalence with the browser runtime POST. The constructor second constant at 0x0044C4FC is still under investigation.
 
## Correction — run 25 address/symbol verification (2026-11-14)

Run 25 (`43580008821`, artifact `14108665890`) exposed incorrect target labels in the preceding analysis step. The TD32 symbol at `0x004CD154` is `TWordViwer.WordAppDocumentBeforeSave`, not `WordAppDocumentBeforeClose`. The LoadDocument/OnTmrAutoSave registration code at `0x004B8C9C–0x004B8CCE` explicitly stores `0x004CD154` at callback field `+0x80`, `0x004CD54C` at `+0x90`, and `0x004CD9C0` at `+0x98`; the conditional callback at `+0x88` is `0x004D00AC` or `0x004CE030`. Thus `0x004CD154` is conclusively the registered BeforeSave callback. Do not call it a close callback.

The actual TD32 procedure named `TWordViwer.WordAppDocumentBeforeClose` begins at `0x004CCBBC`, but its only direct immediate caller found is `FillImgFldsForPrint` at `0x004CCF8F`; no registration reference was found in the scanned raw pointer data. Therefore its name alone does not prove that this procedure is the live Word application close-event handler.

A second address error: `0x00430070` is `TWordDocument.SaveAs2000`, not a Close wrapper. The actual `TWordDocument.Close` overload procedures are TD32-labeled at `0x0042FEB0`, `0x0042FF08`, `0x0042FF7C`, and `0x0042FFF4`; the latter is the three-argument overload. A three-argument Close invocation in the callback body dispatches through document interface VMT slot `+0x29C`, but the exact runtime target for that interface dispatch must be established by matching the interface VMT and wrapper semantics, not by assigning `0x00430070`.

Run 25 itself completed successfully, but its added trace commands targeted the wrong symbols for a close-event investigation. Treat its other outputs as useful only where the TD32 labels and address semantics are independently verified. Next analysis must trace the actual Close overload(s), find the genuine callback registration (if present), and distinguish the BeforeSave callback from document-close lifecycle. No claim about the page-side POST is changed by this correction.


## Run 26 correction — registered BeforeSave vs actual Close wrappers (2026-11-14)

Run 26 (43584217243, artifact 14109926135) completed successfully and supersedes the earlier incorrect callback description in the LoadDocument section above:

- Callback 0x004CD154, registered at viewer field +0x80 in 0x004B8C9C–0x004B8CCE, is TWordViwer.WordAppDocumentBeforeSave, not BeforeClose.
- The actual TD32-named TWordViwer.WordAppDocumentBeforeClose is 0x004CCBBC. Its only direct bounded caller found is FillImgFldsForPrint at 0x004CCF8F; no raw-pointer registration reference was found. Its active event role remains unproven.
- The registered BeforeSave routine checks _Document.Saved through interface slot +0xD8. If changed and the viewer prompt flag is enabled, it presents the changed-document prompt. Cancel sets COM event Cancel to 0xFFFF; Yes/No lead to the three-argument TWordDocument.Close wrapper at 0x0042FFF4.
- Close overload dispatch: no-argument 0x0042FEB0 -> slot +0x4D4; one-argument 0x0042FF08, two-argument 0x0042FF7C, and three-argument 0x0042FFF4 -> slot +0x29C.
- 0x004CB108 is PreparePrintDocument; 0x00430070 is SaveAs2000, not Close.

This correction is explicit because the earlier paragraph above misidentified the registered callback. The relationship between BeforeSave, user-initiated document close, and the web page's close-time POST remains unresolved. The user's observed behavior that changes apply on close even without Save remains a product requirement. Next: resolve the COM target behind +0x29C and trace the parent page's postMessage handler and localhost POST body/response. Do not claim native Linux runtime support from this analysis.


## Run 29 — field lookup / temporary cleanup correction (2026-11-14)

Run 29 (`43589571290`, artifact `14111108881`) completed successfully and narrows two previously over-interpreted candidate paths:

1. `TWordViwer.GetDocFieldName` (`0x004BB81C–0x004BC16F`) calls `SilentSaveEmwatDoc` (`0x004D23D8`) only when a field-name value returned through interface slot `+0xAC` fails a comparison against a static string. This is a conditional fallback during field-name resolution. It is not evidence of a close event or a close-time HTTP request.
2. The previously traced SilentSave callees are print-options routines: `0x004AEA78` is `TfrmWordPrintOption.SetLetterReceivers`; `0x004AEBBC` is `TfrmWordPrintOption.FreePrinters`. Do not describe them as generic save/close helpers.
3. `DeleteTempRAW` (`0x0044AE98–0x0044B053`) calls `Emwat.Sys.CloseAllWords` at `0x0044B01C` after its temporary-file/process checks. The `CloseAllWords` body composes four strings and calls `0x0044B0F8`; TD32 identifies that target as `Emwat.Sys.GetFileVersion`. The evidence therefore does not prove that `CloseAllWords` actually closes Word processes. Its only direct caller found is the RAW cleanup path, not the main letter connector.

No close-time POST trigger, response correlation, or final document-application behavior was recovered in this run. Keep the user's tested apply-on-close behavior as a product requirement, not a claim explained by this static trace. The server-side `EditWordDocument → LoadDocument → AResponseInfo.ContentText → WriteContent` path remains confirmed; the page-side `postMessage` sender and close-time response consumer remain the decisive unresolved targets.


## User repeat-test clarification — Save button is not required (2026-11-14)

The user confirmed by repeating the test that the document appears/is registered in Almas Gam after Word is closed even though the user never presses Save. This confirms the product-level close-to-registration behavior, but it does not establish whether Word saves internally during the close sequence.

A plausible, not-yet-proven lifecycle is: close begins → Word/EMWAT performs a normal or silent save → EMWAT obtains the resulting document/artifact → the local HTTP response returns the final state to the browser → Almas Gam registers it. Do not present this sequence as established fact until the COM call and payload/response are traced.

Next analysis should correlate the exact close event with Word COM Save/SaveAs/Close calls and the HTTP response body. Distinguish the user not pressing Save from the application not saving at all.


## Runtime confirmation of the parameter element name and Linux parser (2026-11-14)

The previously unresolved parameter child element name is now confirmed by the user's captured close-time HTTP response prefix:

`<?xml version="1.0" encoding="utf-8" ?><emwat version="1.0"><method class="EditWordDocument"><param name="wordConfig">`

This is direct runtime evidence for the outer structure `emwat version="1.0"` → `method class="..."` → `param name="..."`. It supersedes the earlier statement that the parameter element tag was unknown for this observed response. It does not prove that every historical method uses only this element or reveal all XML formatting/encoding details.

A conservative parser was added at `python/src/emwat_linux/protocol.py`. It validates UTF-8, the versioned root, one method, the `class` attribute, `param` children and unique `name` attributes. It preserves parameter text as opaque strings and deliberately does not decode Base64, interpret document fields, or assign meaning to `invoke`. It rejects DTD/entity declarations, nested parameter markup, duplicate parameter names and malformed envelopes. Tests: `python/tests/test_protocol.py`.

The service-side source also confirms distinct query branches for `invoke`, `init` and `heartbeat`; however, exact heartbeat response semantics and init response bytes are still not recovered. Do not synthesize either response yet.


## Parser/dispatcher implementation checkpoint (2026-11-14)

Runtime evidence from the close-time response confirms the `param` element name for the observed `EditWordDocument` response. The Python parser now validates the outer UTF-8 envelope and preserves parameter values without decoding them. The explicit dispatcher accepts only handlers registered by the application; unknown method names produce 501 and malformed XML produces 400. It does not dynamically resolve Delphi class names or synthesize a success response.

The HTTP server now requires an exact allowed Origin by default, validates Host against its IPv4 loopback listener, enforces request/response limits and socket timeouts, rejects duplicate Content-Length and sanitizes handler failures. CI run #20 (`43592721635`, commit `2fa217ae83f33b80a7799ede4c75f2cc58b40d76`) passed all 24 tests.

The service's static dispatcher has separate `invoke`, `init`, and `heartbeat` branches. Their presence is confirmed; exact heartbeat/init responses are not. Next implementation work should recover these contracts and the final close-time document payload before implementing the real `EditWordDocument` method.


## Run 89 — مسیر ورودی wordBody در LoadDocument

Workflow #89 (43592922191) با موفقیت اجرا شد و artifact 14113237316 بررسی شد:

- 0x00457050 در TD32 تابع Emwatutils.Finalization از ماژول EmailUtil است. LoadDocument آن را روی ورودی UnicodeString صدا می‌زند؛ تابع دو مقدار global را با رشته ورودی مقایسه می‌کند. معنی آن مقادیر تا decode شدن رشته‌ها نامعلوم است.
- 0x00454B9C تابع Emwatutils.euGetASFileName(UnicodeString, UnicodeString) است و در مسیرهای TIFF/image نیز caller دارد. در نتیجه باید آن را یک تبدیل/نرمال‌سازی مرتبط با نام فایل بررسی کرد، نه parser اختصاصی بدنه Word.
- LoadDocument پس از این مرحله از thunkهای runtime/import برای کار با طول و داده رشته استفاده می‌کند، یک object از طریق global 0x0062F800 و helper سازنده 0x004041BC ایجاد می‌کند و virtual slot +0x10 را با data pointer و length فراخوانی می‌کند.
- تا زمان شناسایی کلاس مقصد و decode رشته‌های ثابت، نوع فایل/stream و semantics دقیق wordBody قطعی نیست. این شواهد به‌تنهایی قرارداد HTTP یا payload پاسخ هنگام بستن Word را مشخص نمی‌کند.


## شواهد نام فایل در ورودی LoadDocument
در artifact مربوط به Run 89 رشته دقیق `DocFileName can not be null.` در تابع LoadDocument دیده می‌شود. مسیر کنترل، رشته محلی حاصل از تبدیل ورودی را از نظر طول بررسی می‌کند و در حالت خالی به این خطا می‌رود. این شاهد قوی است که مقدار ورودی در این لایه به‌عنوان نام فایل سند تفسیر می‌شود؛ هرچند نام پارامتر بیرونی connector همچنان `wordBody` است.

همان تابع رشته‌های `word-document`، `ConfigXML data loaded.` و `Word Calling Mode: ` را دارد. helper پیش از آن نیز شامل ثابت‌های `.doc` و `.docx` است. نتیجه Run 90 نشان داد object مقصد `TFileStream` است؛ بااین‌حال نوع دقیق محتوای ورودی، encoding، نام/مسیر فایل و semantics کامل خواندن مجدد هنوز نیازمند trace بیشتر است.


## Run 90 — شناسایی File Stream و مسیر نوشتن ورودی
Run #90 مشخص کرد که `0x004041BC` thunk مربوط به `rtl230.bpl!TFileStream.Create(UnicodeString, Word)` است. در `LoadDocument`، نام فایل از یک رشته محلی به سازنده داده می‌شود؛ سپس virtual slot `+0x10` روی stream با data pointer و length مشتق‌شده از ورودی `wordBody` فراخوانی می‌شود. بنابراین در این مرحله ورودی به‌عنوان داده‌ای که در یک فایل نوشته می‌شود مصرف می‌شود و نام فایل مقصد از رشته جداگانه‌ای می‌آید.

این یافته تفسیر قبلی را دقیق‌تر می‌کند: مقدار بیرونی `wordBody` صرفاً نام فایل نیست؛ مسیر اولیه `LoadDocument` آن را به‌صورت رشته مدیریت می‌کند، اما سپس محتوای آن را به یک فایل stream می‌نویسد. هنوز مشخص نیست این رشته حامل Base64، متن/بایت‌های سند با encoding خاص یا محتوای دیگری است؛ همچنین مسیر دقیق فایل و واحد طول باید بررسی شود. وجود رشته‌های `base64`، `image/tif` و `Word document file created.` در همین تابع قرینه زمینه‌ای است، نه اثبات قالب دقیق `wordBody`.

`0x00457050` با نام TD32 `Emwatutils.Finalization` و `0x00454B9C` با نام `Emwatutils.euGetASFileName` شناسایی شدند؛ هیچ‌کدام parser بدنه Word نیستند. مسیر HTTP response شناخته‌شده است، اما close-time POST و قرارداد payload نهایی همچنان باز است.

در ادامه `LoadDocument`، همان کلاس `TFileStream` بار دیگر در `0x004B7C3E` با همان filename مشتق‌شده و mode صفر ساخته می‌شود. کد اندازه stream را می‌گیرد و سپس virtual slot `+0x0C` را با buffer/count صدا می‌زند؛ این با خواندن مجدد فایل سازگار است. نام دقیق متد و semantics buffer تا بررسی VMT کلاس در RTL باز می‌ماند.


## Run 91 — تأیید TFileStream.Write و TFileStream.Read
Run #91 (43595953793) import/VMT slot 0x0062F800 را به کلاس TFileStream در rtl230.bpl و 0x004041BC را به سازنده TFileStream.Create(UnicodeString, Word) resolve کرد. در نخستین مسیر ساخت فایل، mode برابر 0xFF00 (fmCreate) است و virtual slot +0x10 با pointer/count فراخوانی می‌شود؛ در layout استاندارد TStream این slot متد Write است. در مسیر دوم، همان کلاس با mode صفر (fmOpenRead) باز می‌شود و slot +0x0C با buffer/count فراخوانی می‌شود که متد Read است.

پس در LoadDocument یک چرخه واقعی ایجاد/نوشتن فایل و سپس بازکردن/خواندن آن وجود دارد. هنوز مسیر دقیق فایل، نوع encoding بایت‌ها و مصرف‌کننده نهایی داده خوانده‌شده مشخص نشده است. helperهای 0x00401270، 0x004012E0 و 0x00401348 به slotهای .idata حل‌نشده می‌روند؛ تا زمان resolve دقیق، آن‌ها را به UnicodeString/Base64 helper خاصی نسبت نمی‌دهیم. همچنین این یافته به‌تنهایی سازوکار POST هنگام بستن Word را روشن نمی‌کند.


## Run 92 — مسیر پس از خواندن فایل و زیرسامانه تصویر/TIFF

Workflow #92 (43597403349، commit `9a631d2ebb3958bc97cc89c02a92a5f6e8f21264`) با موفقیت اجرا شد؛ artifact شماره 14114738491 بررسی شد.

- در `LoadDocument`، پس از مسیر بازکردن فایل واسط با `fmOpenRead` و فراخوانی `TFileStream.Read`، تابع `0x004B8A84` در `0x004B7A58` فراخوانی می‌شود. TD32 این تابع را `TWordViwer.OnTmrAutoSave` معرفی می‌کند. این نام و محل فراخوانی نشان می‌دهد کنترل پس از خواندن داده وارد منطق AutoSave/مدیریت Word می‌شود؛ اما به‌تنهایی ثابت نمی‌کند که این تابع همان callback بستن سند یا ارسال پاسخ HTTP است. باید بدنه و مسیرهای فراخوانی آن جداگانه تحلیل شوند.
- تابع `0x004D1454` با نام `TWordViwer.AddCustomDocPropertiesToDic` در `LoadDocument` مستقیماً فراخوانی می‌شود. بدنه آن مجموعه‌ای از مقادیر را از ساختار سند/COM می‌خواند، رشته‌ها را به اجزای کلید/مقدار تقسیم می‌کند و رکوردهایی را به یک مجموعه/دیکشنری اضافه می‌کند. نام تابع با افزودن Custom Document Properties به دیکشنری سازگار است؛ جزئیات دقیق delimiter و ساختار رکوردها هنوز باید با trace helperها و محل مصرف مقایسه شود.
- تابع `CreateTIFF.SeparteImages` در ماژول `EmwatDocPrintHandlerUnit` یک مسیر مستقل و نسبتاً بزرگ برای جداسازی/پردازش تصاویر TIFF است. اسکن caller مستقیم در محدوده TD32 هیچ `CALL` مستقیمی پیدا نکرد؛ بنابراین فعلاً نمی‌توان آن را به‌عنوان بخشی از مسیر اصلی `LoadDocument` یا پاسخ HTTP معرفی کرد. احتمال dispatch غیرمستقیم/VMT یا فراخوانی از مسیر دیگری همچنان باز است.
- `CreateImageFile` در همان ماژول، روی مجموعه‌ای از ورودی‌ها حلقه می‌زند، نام/مسیر فایل را از داده‌های هر مورد می‌سازد و `PrintWordDoc` را برای نوشتن فایل فرا می‌خواند. `PrintWordDoc` یک `TFileStream` با حالت `fmCreate` می‌سازد و داده را از طریق virtual slot استاندارد `TStream.Write` می‌نویسد. در صورت موفقیت، کد از مسیر ادامه/ثبت مورد عبور می‌کند؛ این شاهدی برای تولید فایل‌های تصویری مجزا در مسیر چاپ/تصویر است، نه اثبات upload یا ارسال آن‌ها به مرورگر.
- اسکن caller مستقیم برای `CreateImageFile` و `CreateTIFF.SeparteImages` در محدوده‌های بررسی‌شده نتیجه‌ای نداد. این نتیجه فقط نبودن immediate CALL مستقیم در محدوده TD32 اسکن‌شده را ثابت می‌کند؛ فراخوانی غیرمستقیم، event، callback یا entrypointهای خارج از محدوده را رد نمی‌کند.

**گام بعدی:** trace کامل `OnTmrAutoSave` و فراخوان‌های مستقیم/غیرمستقیم آن؛ شناسایی زمان‌بندی timer و عملیات Word COM داخل آن؛ سپس trace callerها و VMT/registration مسیر TIFF و چاپ. هدف همچنان یافتن event واقعی بستن Word و اتصال Save/Close به بدنه پاسخ HTTP است. از نام تابع‌ها به‌تنهایی نتیجه‌گیری نمی‌کنیم.


## Run 94 — تفکیک OnTmrAutoSave از عملیات واقعی ذخیره و ثبت رویدادهای OLE

Workflow #94 (43598550321، commit `ea721080388e7d1903a6fb67af08abcf300c8f7c`) موفق شد؛ artifact شماره 14115756587 بررسی شد.

- TD32 نام تابع `0x004B8A84` را `TWordViwer.OnTmrAutoSave` ثبت می‌کند؛ اما caller مستقیم پیدا‌شده در محدوده TD32 فقط `TWordViwer.LoadDocument` در 0x004B7A58 است. بنابراین در مسیر بررسی‌شده این تابع در زمان LoadDocument فراخوانی می‌شود؛ اسم نماد به‌تنهایی اثبات نمی‌کند که این فراخوانی یک tick زمان‌سنج یا عملیات ذخیره فایل است.
- بدنه تابع رشته‌های `wv.LoadDocument method called.`، `config.view mode:`، `connecting to Ole Word Engine.`، `connected.` و `Init word engine finished.` را مصرف/ثبت می‌کند. همچنین وضعیت‌های view/readonly/protected را از شیء پیکربندی می‌خواند.
- تابع، چند callback را روی شیء متصل به Word/OLE ثبت می‌کند: آدرس‌های 0x004CD154، 0x004CD54C و 0x004CD9C0؛ سپس بسته به flag موجود در شیء WordViewer یکی از 0x004D00AC یا 0x004CE030 را در slot مربوطه قرار می‌دهد. این ثبت callback در مسیر LoadDocument شاهد مستقیم است؛ معنای دقیق هر event باید از بدنه handler و قرارداد COM/اتصال event sink تعیین شود.
- تابع 0x004CDB54 که در همین بدنه فراخوانی می‌شود، در TD32 با نام `TWordViwer.QuitWord` شناسایی شد. بنابراین این helper یک check مرتبط با QuitWord است، نه silent-save helper.
- تابع 0x004C5D68، `TWordViwer.SetDocCaption` است؛ دو property/مقدار را از شیء Word می‌خواند و flagهای داخلی caption/viewer را تنظیم می‌کند.
- آدرس‌های 0x004D68D4 و 0x004D531C که ابتدا به‌عنوان helperهای احتمالی OnTmrAutoSave بررسی شدند، در واقع `TDictionary<UnicodeString,TXmlWordConfigTwinField>.Remove` و `TDictionary<UnicodeString,TXmlWordConfigField>.Remove` هستند و caller مستقیم‌شان `AddCustomDocPropertiesToDic` است. آن‌ها بخشی از مسیر AutoSave نیستند.
- رشته `<Office LISENCE>: Word is not activated. Close Method.` در همین تابع دیده می‌شود؛ این فقط پیام مربوط به وضعیت فعال‌سازی Word است و قرارداد close-time را مشخص نمی‌کند.
- مسیر AutoSave و event registration هنوز باید تفکیک شوند: handlerهای ثبت‌شده در run بعدی trace می‌شوند تا Save/Close/BeforePrint و ارتباط احتمالی‌شان با پاسخ HTTP معلوم شود. تا این مرحله هیچ close-time POST جدیدی اثبات نشده است.


## Run 95 — Word event callback handlers (2026-11-14)

Workflow run `43599550286` completed successfully; artifact `14115498934` was inspected. This pass traced the five callback addresses assigned/referenced by the Word setup path.

### Handler identities established by TD32

| VA | TD32 procedure | What is established |
|---|---|---|
| `0x004CD154` | `TWordViwer.WordAppDocumentBeforeSave` | BeforeSave handler, not BeforeClose. It checks document state, prompts for registration/confirmation, and can cancel or call the 3-argument document Close interface slot. |
| `0x004CD54C` | `TWordViwer.WordAppNewDocument` | New-document event handler. It checks viewer/document state and conditionally changes document flags and invokes document interface methods. No HTTP POST/response behavior identified in this trace. |
| `0x004CD9C0` | `TWordViwer.WordAppWindowActivate` | WindowActivate handler. It invokes a document interface VMT slot `+0x29C`; the semantic meaning of that slot remains unresolved. |
| `0x004CE030` | `TWordViwer.WordAppDocumentBeforePrintBGPrint` | BeforePrint/BGPrint handler. Long handler includes document/print configuration and printer-related calls; no evidence in this pass that it returns the edited document to Almas Gam. |
| `0x004D00AC` | `LoadOptions` | Options-loading routine, not a Word lifecycle event by its TD32 name. |

### Registration and limits

The immediate-reference scan finds `0x004CD154` and `0x004CD54C` being stored into callback-like object fields by `TWordViwer.OnTmrAutoSave` at `0x004B8CA2` and `0x004B8CB8`. This is consistent with callback registration during `LoadDocument`, but the exact external COM event/interface contract is not yet proven. The same setup routine also writes a further callback pointer at object offset `+0x9C`; the relevant complete assignment sequence must be interpreted with its surrounding code before assigning event semantics to every field.

The direct-call scans report no direct immediate CALL xrefs for the five handler entry points. This does **not** mean the handlers are unused: COM event sinks and callback tables commonly invoke them indirectly. Conversely, a TD32 procedure name alone is not proof that an event is actively wired at runtime.

The separate TD32 procedure `TWordViwer.WordAppDocumentBeforeClose` at `0x004CCBBC` remains distinct. Its only direct caller found is `FillImgFldsForPrint` at `0x004CCF8F`; no active registration for it was established. Do not conflate it with `WordAppDocumentBeforeSave`.

### Consequence for the Linux bridge

Run 95 still does not establish the close-time request/response contract, whether the Word document is serialized on close, or which callback triggers the Almas Gam registration. The user's observed behavior remains important operational evidence: closing Word is sufficient for the file to appear in Almas Gam, without manually pressing Save. The native Linux implementation must reproduce that observable behavior, but must not invent the hidden Windows callback or payload semantics.

Next reverse-engineering target: follow the callback-table construction and indirect dispatch path from `OnTmrAutoSave`, resolve the Word interface VMT slots used by `WordAppNewDocument` and `WordAppWindowActivate`, and trace the full BeforePrint handler's data outputs separately from the editor's close/return path.


## Run 96 — callback record layout and conditional Word event wiring (2026-11-14)

Workflow run `43600693760` succeeded; artifact `14116641628` was inspected.

The full instruction sequence in `TWordViwer.OnTmrAutoSave` (`0x004B8A84`) gives stronger evidence than the earlier isolated immediate-reference scan. It obtains a Word-related object at `viewer + 0x44` and writes callback/context pairs into that object's fields:

| Callback field | Context field | Callback VA | TD32 identity |
|---|---|---|---|
| `+0x80` | `+0x84` | `0x004CD154` | `WordAppDocumentBeforeSave` |
| `+0x90` | `+0x94` | `0x004CD54C` | `WordAppNewDocument` |
| `+0x98` | `+0x9C` | `0x004CD9C0` | `WordAppWindowActivate` |
| `+0x88` | `+0x8C` | conditional | `LoadOptions` (`0x004D00AC`) or `WordAppDocumentBeforePrintBGPrint` (`0x004CE030`) |

The fourth callback is selected by testing byte `[viewer + 0x3C]`: nonzero selects `LoadOptions`; zero selects `WordAppDocumentBeforePrintBGPrint`. A later branch in the same routine also assigns `0x004D00AC` or `0x004CE030` to the same callback field, so the final effective value depends on the complete runtime branch path. This is evidence of an explicit callback/context record layout, but the exact external event source and dispatch ABI remain unresolved.

Raw pointer scans found the handler addresses in executable code at the expected assignments, not in unrelated static data. The TD32 immediate-reference scans likewise identify the assignments inside `OnTmrAutoSave`. Direct CALL scans still show no direct calls to the callback handlers, consistent with indirect callback invocation.

The helper at `0x0043F360` is `TWordApplication.Get_ScreenUpdating`; `0x00440950` is `Get_DisplayAutoCompleteTips`; and `0x00441C68` is `TWordApplication.Quit`. These are Word automation property/method wrappers and should not be mistaken for save/close transport. `0x00404FBC` has no TD32 procedure boundary in the current symbol data.

Still unproven: whether any of these callbacks causes the edited document to be serialized or POSTed after the user closes Word; the result envelope and exact payload remain unknown. The confirmed user-observed close-to-Almas behavior remains a product requirement, not a license to infer the implementation.

## 2026-11-14 — Run 97: ادامهٔ مسیر ثبت callbackهای Word

اجرای GitHub Actions شمارهٔ 97 با commit 58acba41c4622137a94c97bf171cc3890d26fd5d موفق شد؛ artifact با شناسهٔ 14117102104 دریافت و فایل‌های disassembly آن بررسی شدند.

### نتیجه‌های قطعی جدید

- در انتهای TWordViwer.OnTmrAutoSave، بعد از ثبت callbackهای اصلی، متد 0x004C5D68 اجرا می‌شود. این متد از شیء OLE در offset viewer+0x44 دو property را می‌خواند: از VMT slot +0x15C یک مقدار word و از slot +0x104 یک مقدار byte؛ سپس آن‌ها را در viewer+0x4C و viewer+0x4D ذخیره می‌کند. نام معنایی propertyها از شواهد فعلی مشخص نیست.
- در مسیر دیگر، 0x004CDB54 روی مقدار viewer+0x44 کار می‌کند، یک رشته/مقدار را می‌خواند و تابع System.Pos(UnicodeString, UnicodeString) را از طریق thunk 0x00401398 فراخوانی می‌کند. خروجی تابع به Boolean تبدیل می‌شود. بنابراین این helper یک بررسی مبتنی بر جست‌وجوی زیررشته است؛ هنوز معنای رشتهٔ مورد جست‌وجو و شرط اجرایی آن مشخص نیست.
- 0x00404FBC برخلاف ابهام قبلی، یک thunk به vcl230.bpl!TOleServer.SetConnectKind است. در OnTmrAutoSave روی شیء OLE با آرگومان 1 فراخوانی می‌شود. این شواهد اتصال به OLE server را تقویت می‌کند، اما به‌تنهایی نوع دقیق اتصال یا چرخهٔ event sink را اثبات نمی‌کند.
- thunk 0x004013F8 به System.DynArrayClear می‌رسد و در OnTmrAutoSave برای پاک‌سازی آرایه‌های محلی/ساختاری استفاده شده است؛ callback dispatcher نیست.
- thunk 0x00401368 به System.UStrCat و thunk 0x00401398 به System.Pos می‌رسند. این‌ها helperهای عمومی رشته‌اند، نه dispatcherهای event.
- در بخش teardown مربوط به OnTmrAutoSave، در یک شاخه TWordApplication.Quit فراخوانی و سپس VMT slot +0x54 روی شیء OLE صدا زده می‌شود. در شاخهٔ دیگر callback دیگری در slot +0x88/+0x8C جایگزین و دو VMT slot دیگر (+0x100 و +0x108) روی interfaceهای گرفته‌شده از OLE فراخوانی می‌شوند. معنای دقیق slotها هنوز نیازمند resolution جدول interface/VMT است.

### مرز شواهد

- وجود callback pointerها در ساختار viewer+0x44 همچنان تأیید می‌شود، ولی consumer و ABI دقیق اجرای آن‌ها هنوز پیدا نشده است.
- WordAppDocumentBeforeClose در 0x004CCBBC یک procedure واقعی و مستقل است؛ در بدنه‌اش از چند interface call با slot +0x38 و یک helper در 0x004BCA88 استفاده می‌شود. تنها direct caller شناخته‌شده همچنان FillImgFldsForPrint است. بنابراین هنوز مدرکی نداریم که این handler، رویداد اصلی بستن سند در editor باشد.
- در این run هیچ POST، XML response یا payload مربوط به زمان بستن Word اثبات نشد.
- مشاهدهٔ کاربر مبنی بر ثبت تغییرات هنگام بستن Word همچنان یک الزام رفتاری قطعی برای بازسازی است؛ اما اتصال آن به یک handler مشخص در باینری هنوز اثبات نشده است.

Run 98 برای trace کردن 0x004BCA88، helperهای وضعیت/گزینهٔ viewer و slotهای teardown اضافه شد.

## اصلاح و تکمیل Run 98 — 2026-11-14

بررسی artifact شمارهٔ 98 چند نام‌گذاری را دقیق کرد و لازم است برداشت موقت Run 97 اصلاح شود:

- آدرس `0x004CDB54` طبق TD32 نام `TWordViwer.QuitWord` دارد. این تابع مقدار یک property از شیء OLE در `viewer+0x44` را می‌خواند، آن را به رشته تبدیل می‌کند و با `System.Pos` در برابر literal واقع در `0x004CDC14` جست‌وجو می‌کند. اگر substring پیدا شود، نتیجهٔ تابع False است؛ اگر پیدا نشود، نتیجه True است. در `OnTmrAutoSave` نتیجه با `test al; jne 0x004B8E39` مصرف می‌شود؛ بنابراین یافتن substring مسیر teardown مستقیم را رد می‌کند و نبودن آن وارد شاخه‌ای می‌شود که پیام/ثبت وضعیت و سپس `TWordApplication.Quit` و چند فراخوانی interface را اجرا می‌کند. متن literal در `0x004CDC14` هنوز decode نشده و شرط معنایی/نام property را نمی‌توان حدس زد.
- `0x004C5D68` طبق TD32 نام `TWordViwer.SetDocCaption` دارد و تنها direct caller آن `OnTmrAutoSave` در `0x004B8E8B` است. بدنه از interface شیء OLE دو property با VMT slotهای `+0x15C` و `+0x104` می‌خواند و نتیجه را در byteهای `viewer+0x4C` و `viewer+0x4D` ذخیره می‌کند. این نام نمادین با رفتار مشاهده‌شده در بدنه یکسان‌سازی معنایی نشده است؛ بنابراین آن را «options sync» قطعی نمی‌نامیم.
- `0x004BCA88` نام TD32 آن `TWordViwer.GetXmlFieldInfo` است؛ یک procedure بزرگ با اندازهٔ 12,688 بایت. این helper در دو محل از `GetCaptionItemFont` و یک محل از `WordAppDocumentBeforeClose` فراخوانی می‌شود. پس helper عمومی استخراج اطلاعات XML/field است، نه helper اختصاصی close. حضور آن در BeforeClose فقط نشان می‌دهد handler در آن مسیر برای گرفتن اطلاعات field از آن استفاده می‌کند.
- بدنهٔ `WordAppDocumentBeforeClose` (`0x004CCBBC`) روی داده‌های دو مجموعه در فیلدهای `+0xE8` و `+0xEC` از شیء جاری، مقادیر index/field را می‌سازد، دو فراخوانی interface در slot `+0x38` انجام می‌دهد و سپس `GetXmlFieldInfo` را فراخوانی می‌کند. این با آماده‌سازی/خواندن اطلاعات field سازگار است، ولی به‌تنهایی اثبات نمی‌کند این event handler در مسیر عادی بستن سند ثبت شده باشد.

Run 99 برای decode کردن literal شرط QuitWord و بررسی interface tableها اجرا شده است. تا دریافت نتیجه، متن شرط و معنای slotهای teardown باز می‌ماند.


## Run 101 — تفکیک شرط فعال‌سازی Office از چرخه بستن سند (2026-11-15)

- GitHub Actions workflow run #101 با شناسه `43680106253` روی commit `cdf542e4bd486a63d92a1b26c41a05f30028ae70` با موفقیت پایان یافت؛ artifact `14148322936` دریافت و بررسی شد.
- خطای Run 100 صرفاً از فراخوانی scanner بدون آرگومان selector لازم بود؛ workflow با selector صریح `*` اصلاح شد و Run 101 کامل شد.
- literal در `0x004CDC14` اکنون decode شده است: `Activation` (UTF-16LE). تابع `TWordViwer.QuitWord` در `0x004CDB54` این substring را در رشته‌ای که از property شیء OLE در `viewer+0x44` می‌خواند جست‌وجو می‌کند.
- اگر `Activation` پیدا شود، `QuitWord` مقدار False می‌دهد؛ اگر پیدا نشود، True می‌دهد. در caller یعنی `OnTmrAutoSave`، نتیجه True شاخه‌ای را فعال می‌کند که پیام `<Office LISENCE>: Word is not activated. Close Method.` را ثبت/نمایش می‌دهد و سپس `TWordApplication.Quit` را فراخوانی می‌کند. بنابراین این شاخه کنترل فعال‌سازی Office و خروج از Word است؛ مدرکی برای ذخیره سند یا ارسال آن به Almas Gam نیست.
- در resourceهای BPL، فرم `TEmSettingForm` شامل کنترل‌های `rbAutoSave`، `rbDontSave`، `chkDntAskForSave` و `cbbAutoSaveInterval` است. این‌ها وجود تنظیمات ذخیره خودکار/عدم ذخیره و فاصله زمانی را ثابت می‌کنند، اما به‌تنهایی نشان نمی‌دهند که کدام گزینه در نصب کاربر فعال بوده یا مسیر ثبت نهایی نامه چگونه عمل می‌کند.
- یک مسیر جدا در ماژول `uSendLog` شناسایی شد: `TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` در `0x005EC580`، تابع `CloseWordApp` در `0x005EBDA8` را فراخوانی می‌کند؛ caller دیگر `btnShowFileClick` است. نام کلاس، فرم `TfrmShowAutoSaveFiles` و callerهای مستقیم نشان می‌دهند این handler متعلق به پنجره نمایش فایل‌های AutoSave است، نه اینکه لزوماً handler اصلی ویرایش نامه باشد. بدنه CloseWordApp روی مجموعه‌ای از اشیای Word/Document loop می‌زند و متدهای interface را صدا می‌زند؛ معنای دقیق هر slot هنوز resolve نشده است.
- این مسیر جدا را نباید با `TWordViwer.WordAppDocumentBeforeClose` در `0x004CCBBC` یکی دانست. دومی همچنان فقط caller مستقیم شناخته‌شده `FillImgFldsForPrint` دارد.
- نتیجه منفی پابرجاست: Run 101 هیچ close-time POST تازه، payload نهایی، یا اتصال اثبات‌شده‌ای از `CloseWordApp` به پاسخ HTTP ارائه نکرد.
- گام بعد: trace بدنه `TEmSettingForm` و ذخیره/خواندن گزینه‌های AutoSave، resolve کردن interface slotهای `CloseWordApp`، و بررسی اینکه callbackهای ثبت‌شده در WordViewer چگونه به مسیر پاسخ نهایی `EditWordDocument` می‌رسند. تا آن زمان production handler یا close protocol حدس زده نشود.


## Run 102 — AutoSave settings and separate AutoSave viewer lifecycle

- GitHub Actions run #102 (43681595513, commit 168793fd5e2dfaeff6036894409e7a5385944d31) completed successfully; artifact 14148712060 was inspected.
- TEmSettingForm.chkDntAskForSaveClick at 0x005EAA20 opens the current-user registry hive (0x80000001, HKCU) and performs multiple registry value writes. The values include settings associated with controls at instance offsets +0x3E0, +0x3D8, +0x3C4, +0x3C8, +0x3CC, and the AutoSave interval control at +0x3F4. For interval values 1–5 it multiplies a lookup-table value by 1000; otherwise it writes 0x2710 (10000 ms). Registry value names and complete semantic mapping still require resolving the referenced string constants and registry helper APIs.
- The settings resource confirms controls rbAutoSave, rbDontSave, chkDntAskForSave, chkSaveIOxmls, and cbbAutoSaveInterval. This proves the UI exposes AutoSave-related options; it does not prove which options were selected in the user's session or how the main editor's final registration works.
- TEmSettingForm.FormCreate at 0x005EAD94 delegates to inherited form creation, then invokes helper 0x00402A50 and 0x0040496C; those helper semantics and the exact read-side settings mapping remain unresolved.
- The small btnOkClick handler at 0x005EAA14 calls TCustomForm.Close via thunk 0x00404E84; it does not itself show persistence logic. The checkbox click handler is the one containing registry operations.
- The separate TfrmShowAutoSaveFiles.FormClose at 0x005EBF20 is called from its own Delete/FormCreate/finalization paths. Its WordAppDocumentBeforeClose callback at 0x005EC580 calls CloseWordApp only when a document interface's first word equals 0x2E; this is tied to the AutoSave-files viewer, not proven to be the main Word editor's close event.
- CloseWordApp at 0x005EBDA8 iterates a Word Documents collection, conditionally inspects/updates document items, and invokes interface slot +0x29C; exact COM method semantics remain unresolved. It does not establish an HTTP POST or final registration payload.
- No evidence in Run 102 links these registry settings or the AutoSave viewer teardown to the main editor's final Almas Gam registration request. Keep that protocol unknown until a concrete caller/payload/response chain is found.
- Next target: resolve registry helper APIs and string constants to map each setting key/value; separately resolve the +0x29C Word interface slot and identify actual event registration/dispatch for the main viewer's BeforeClose callback. Continue tracing the main editor's save/close-to-HTTP response path without conflating it with the AutoSave viewer.


## Run 103 — registry settings and Word lifecycle follow-up (2026-11-15)

- GitHub Actions run #103 (run ID `43682606812`, commit `b0f92c0f3298b1d92b41906691e84960f75f6ee7`) completed successfully: 36/36 steps; artifact `14149148019` (`emwat-word-lifecycle-analysis`).
- The settings handler `TEmSettingForm.chkDntAskForSaveClick` at `0x005EAA20` confirms a current-user registry flow: it creates/uses a registry object, selects root `HKEY_CURRENT_USER` (`0x80000001`), opens `Software\\Emwat\\Dynamic Config`, writes integer and Boolean values, then releases the registry object. The IAT/thunk map identifies `0x00404414` as `TRegistry.WriteInteger(UnicodeString, Integer)` and `0x00404424` as `TRegistry.WriteBool(UnicodeString, Boolean)`.
- Confirmed value names extracted from the Delphi UTF-16 string headers: `Logging Level`, `Save I/O Trace Files`, `Background Priniting` (original spelling), `Dont Ask Save On Print`, `Save Before Print`, and `AutoSaveInterval`.
- Handler mapping from the observed writes: component/object offsets `+0x3E0` → integer `Logging Level`; `+0x3D8` → Boolean `Save I/O Trace Files`; `+0x3C4` → Boolean `Background Priniting`; `+0x3C8` → Boolean `Dont Ask Save On Print`; `+0x3CC` → Boolean `Save Before Print`; `+0x3F4` → integer `AutoSaveInterval`. For interval selection values 1–5, the selected lookup-table value is multiplied by 1000 before writing; other values write 10000 ms. This is the save-side mapping; don't assume startup reads use the same helper path until found.
- Corrected a prior lead: `TEmSettingForm.FormCreate` at `0x005EAD94` calls `0x00402A50` (`user32!GetDesktopWindow`) and `0x0040496C` (`TWinControl.SetParentWindow`), not registry-read routines. Its short body does not load the persisted settings. The exact settings-load path remains unresolved.
- The `BeforeSave` callback body still performs a prompt and may dispatch the 3-argument Word `Close` overload through interface slot `+0x29C`; direct CALL xref scans do not resolve its callback wiring because the stored function pointer is assigned as data in `OnTmrAutoSave`. This is evidence of callback pointer storage, not yet proof of the COM event-sink ABI or final server registration.
- All four `TWordDocument.Close` overload wrappers were traced. The no-argument overload dispatches slot `+0x4D4`; overloads with one, two, or three optional arguments dispatch slot `+0x29C`. TD32 direct-call scans show no direct CALL xrefs for these wrappers; raw pointer matches occur in debug metadata, so do not infer which overload is used by the main editor solely from those scans.
- No verified close-time HTTP POST, response payload, or final Almas Gam registration operation was found. The user's observed behavior (closing Word without manually pressing Save still registers the document) remains an important runtime fact to reconcile, not a protocol proven by this static trace.
- Next targets: locate the *read-side* registry operations for `Dynamic Config` and the actual settings form initialization; trace callback record consumption / COM connection-point wiring around `OnTmrAutoSave`; identify real main-editor close and final local HTTP request/response chain. Keep the AutoSave files viewer's separate close handler isolated from the main editor.


## Run 104 — registry API scan and post-read range validation (2026-11-15)

Workflow run `43683614577` completed successfully (37/37 steps); artifact `14150300042`.

- The PE import table contains registry-related imports including `advapi32!RegQueryValueExW`, `RegOpenKeyExW`, and Delphi `TRegistry` read/write methods (`ReadBool`, `ReadInteger`, `ReadString`, `WriteBool`, `WriteInteger`, and related methods).
- The first scanner reported zero direct CALL/JMP references to detected import thunks. This is a limitation of that scanner, not evidence that the read APIs are unused: x86 code can call imported APIs through `call dword ptr [IAT]`, and can use register-based indirect calls or wrappers.
- The scanner's first version detected one executable thunk (`0x00624150` → Delphi `TRegistry` destructor) but no direct callers. The report is retained as a negative result with explicit scope limitations.
- The post-read disassembly requested at `0x004B7CFA–0x004B809D` decoded zero instructions because the start address lands in non-code/alignment data after the preceding exception-handling sequence. The valid continuation target observed in the preceding LoadDocument trace is `0x004B7DE1`; the workflow range has been corrected to start there.
- Follow-up commits `743e6378` and `a4027a70` expand the registry scanner to detect absolute IAT-indirect CALL/JMP operands and raw pointer references, and correct the post-read trace range. Their rerun results must be checked before interpreting the new report.

No evidence from Run 104 establishes the exact startup registry-read path, a close-time HTTP POST, or the final Almas Gam registration payload. Continue treating these as unresolved.


## Run 113 — main Word Viewer startup registry reads (2026-11-15)

Workflow run #113 (run ID `43688755518`, commit `caf4412c466cb8dbbbec01c15c853956e731f063`) completed successfully; artifact `14151906706`.

**Correction to the Run 103/104 status:** the startup settings-read path is now located. It is in the main `TWordViwer` constructor at `0x004D0D24–0x004D0FE6`, not in `TEmSettingForm.FormCreate` and not in the short `FormCreate` body previously examined.

The constructor performs this sequence:
- Creates a Delphi `TRegistry` object through `0x004043CC`.
- Sets root key to `HKEY_CURRENT_USER` (`0x80000001`) through `0x004043E4`.
- Opens `Software\\Emwat\\Dynamic Config` through `0x004043EC`, using the UTF-16 string at `0x004D0FF4`.
- If the key opens, checks each value with `TRegistry.ValueExists` (thunk `0x00404454`) and reads existing values with `TRegistry.ReadBool` (thunk `0x0040442C`) or `TRegistry.ReadInteger` (thunk `0x0040441C`).
- Releases the registry object through its destructor path at `0x004043DC`.

Confirmed read-side value mapping from constructor instructions and UTF-16 string constants:
| Registry value | Type | Viewer instance field | Behavior |
| --- | --- | --- | --- |
| `Background Priniting` | Boolean | `+0x3C` | If present, overwrites the constructor default `true` |
| `Dont Ask Save On Print` | Boolean | `+0x3D` | If present, overwrites the constructor default `true` |
| `Save Before Print` | Boolean | `+0x3E` | If present, overwrites the constructor default `false` |
| `AutoSaveInterval` | Integer | `+0x88` | Defaults to `0`; if present, reads integer; values below `10000` are clamped to `10000` |

The interval field is therefore a millisecond value with a 10-second minimum in this constructor. The save-side settings UI previously showed selected interval lookup values multiplied by 1000 before writing, consistent with this unit. Do not infer the actual timer schedule or save operation from the field alone.

The constructor trace does **not** show reads for `Logging Level` or `Save I/O Trace Files`; those remain unresolved and may be handled elsewhere. The exact user-selected values at runtime are also unknown.

This closes the specific question “where does the main Word Viewer read these four Dynamic Config values?” It does **not** close the main-editor document-close/Almas Gam registration question: no close-time HTTP POST, final response payload, or registration commit was established by Run 113. Keep the user's observed close-without-manual-Save behavior as a separate runtime fact to reconcile.


## Runs 116–117 — TETracer registry write path (2026-11-15)

Workflow #116 (run ID `43699248792`, commit `ca88b7d1a2eeb7698d8d72053f5b47b54c51c55b`) completed 37/37 steps; artifact `14155927867`. Workflow #117 (run ID `43703253785`, commit `ed267e0fac1f4f077bf3c92510e5e4c6bd8f9d1e`) completed 38/38 steps; artifact `14158186460`. Both completed successfully.

The expanded registry scan adds useful call-site evidence, but it does **not** establish that the two remaining settings are read at startup:

- The raw pointer reference at `0x00466D16` points to the generic Delphi `TRegistry` import slot. It is a data/reference hit, not a decoded CALL instruction and not proof that this address executes a registry read.
- In the `TETracer.GetUniquePostfix` procedure, the bounded trace at `0x00467C60` shows `0x00467C99` calling the `TRegistry` constructor thunk `0x004043CC`, followed by `SetRootKey(HKEY_CURRENT_USER)` at `0x00467CB7`. Direct call-site context further shows calls at `0x00467D63` to `TRegistry.WriteBool` (`0x00404424`) and at `0x00467D75` to `TRegistry.WriteInteger` (`0x00404414`). Thus this is a **registry write path**, not evidence of `ReadBool` / `ReadInteger`.
- The value-name arguments passed by `TETracer.GetUniquePostfix` are pointers `0x00467F2C` and `0x00467F64`; the current artifact does not decode those strings. Do not map them to `Save I/O Trace Files` or `Logging Level` merely because their types appear plausible.
- The bounded trace for `0x00466CE0–0x00466D40` decodes only its first byte and is not sufficient to identify the function or its behavior. The previous lead around `0x00466D16` remains unresolved.
- Other contexts (`0x00468E0B`, `0x00509245`, `0x005099C1`, and `0x005EAE5D`) also show TRegistry object construction, but the supplied ranges do not by themselves prove that they read either missing setting.

**Current settings status:** the four values read by the main `TWordViwer` constructor remain confirmed by Run 113. `Logging Level` and `Save I/O Trace Files` are confirmed as values written by the settings UI, but their startup/read-side consumers are still not located. Next analysis must recover complete TD32 function boundaries and full disassembly around `TETracer.GetUniquePostfix` (including `0x00467D00–0x00467E80` and the string data at `0x00467F2C` / `0x00467F64`), then search all read-side call paths rather than treating raw IAT references as execution evidence.

No new evidence in Runs 116–117 establishes the main editor's close-time HTTP request, response payload, or final Almas Gam registration operation.


## Parallel reverse-engineering checkpoint — 2026-11-15 (Word, registry, cleanup, and bridge)

### Main Word close/register callback

The focused request-lifecycle analysis confirms the following:

- The main editor event record stores routine 0x004CD154 (TD32 symbol: WordAppDocumentBeforeSave) at offset +0x80. It also stores NewDocument 0x004CD54C at +0x90 and WindowActivate 0x004CD9C0 at +0x98. A settings-dependent callback at +0x88 is either 0x004CE030 or 0x004D00AC.
- The separate routine symbolized WordAppDocumentBeforeClose at 0x004CCBBC is not the pointer installed in that event record. Its only previously identified direct caller is in the FillImgFldsForPrint path.
- Routine 0x004CD154 logs "Document.OnBeforeClose Called." and "Document.OnBeforeClose succeed." Its prompt text is: "محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات مي‌باشيد؟" Buttons are "موافقم", "خیر", and "انصراف".
- Dialog result 2 sets Cancel = -1 and aborts. Result 6 enters the affirmative branch and passes -1 through the SaveChanges variant setup; other non-cancel results pass 0. The non-cancel path calls the Word Document.Close interface slot +0x29C, releases the active document interface, and clears viewer state.
- The method's TD32 symbol says BeforeSave, while its own log strings say OnBeforeClose. The exact COM event name corresponding to callback-record offset +0x80 is still unresolved. Do not silently equate the symbol name with the event-sink slot name.

This is strong evidence for the custom register-changes prompt in the Word close/save lifecycle and is consistent with the user's observed behavior. It does not by itself establish the final HTTP or Almas registration path.

### Registry read-side closure

The earlier Run 116–117 uncertainty about Logging Level and Save I/O Trace Files is superseded by the focused registry runs:

- Main TWordViwer constructor reads HKCU\Software\Emwat\Dynamic Config:
  - Background Priniting (Boolean, viewer +0x3C, default true)
  - Dont Ask Save On Print (Boolean, viewer +0x3D, default true)
  - Save Before Print (Boolean, viewer +0x3E, default false)
  - AutoSaveInterval (Integer, viewer +0x88, default 0, clamped to at least 10000 ms)
- TETracer constructor reads Logging Level (Integer, object +0x10) and Save I/O Trace Files (Boolean, object +0x11) from the same HKCU\Software\Emwat\Dynamic Config subkey.
- TETracer.GetUniquePostfix also uses Save I/O Trace Files and Created IO Trace Count. It decrements the count; when it becomes non-positive it disables Save I/O Trace Files and resets the count to 15, then creates/writes a trace file. This is a bounded diagnostic trace quota, not the letter-registration path.
- The settings-unit Finalization routine reads the six Dynamic Config values into associated controls; its exact lifecycle trigger remains unresolved.
- Image/print tools use a separate HKCU\SOFTWARE\Emwat\PrintParams subkey. Float values are mLeft, mTop, mRight, mBottom; integer values are Posotion (exact spelling), Size, PrintRange.

### Temporary Word-process cleanup

- Exported CloseAllWords (0x0044AE98) enumerates top-level windows with FindWindowW/GetWindow/GetWindowTextW and checks title markers including "GamElectronic EMWAT" and ".doc". On a match it runs taskkill.exe /f /im WINWORD.EXE, sleeps 100 ms, and repeats.
- It then calls an internal helper at 0x0044AD30, which obtains the Windows temp path and invokes exported DeleteTempRAW (0x0044B0F8) on masks including %TEMP%\efg*.*, %TEMP%\~$g*.*, and %TEMP%\temp-emwatwf\*.*.
- Exported DeleteTempRAW (0x0044B0F8) enumerates matches with FindFirst/FindNext, normalizes attributes with FileSetAttr, and deletes them with DeleteFile. Exported GetFileVersion is at 0x0044B2DC and parses version-resource data.
- The export table confirms these external names; TD32 labels at the same addresses are mismatched. No internal caller of exported CloseAllWords was found, so EmwatService.exe may invoke it externally. The external call site remains unknown.


### Request/response timing and Base64 boundary

- Capture stream 18 contains one EditWordDocument POST and one response-word response in the same TCP stream. Packet-level timing shows the full request body completes at 0.002154 s and the first response payload arrives at 54.560037 s, a 54.557883-second server-side wait. The response transfers in about 1.362 ms; two Agent heartbeats occur during the wait. This confirms a long-lived XHR, not merely a slow file transfer.
- TEditWordDocument.PerformMethod calls TWordViwer.LoadDocument synchronously. The successful LoadDocument path assigns AResponseInfo.ContentText and calls TIdHTTPResponseInfo.WriteContent.
- The decoded LoadDocument range does not show an obvious explicit WaitFor/ProcessMessages loop. The OnTmrAutoSave tail at 0x004BA058–0x004BB3AF is compiler cleanup/exception handling, not an identified wait loop.
- LoadDocument writes its wordBody argument bytes directly to the temporary TFileStream. The Base64Decode call at 0x004B7E44 operates on [ebp-8], not the wordBody argument at [ebp-0x1C]; do not claim that this call decodes wordBody. The captured XML wordBody is Base64 text, so the decode may occur upstream in EmwatService's XML/parameter layer; that boundary is not present in the BPL.
- Packet-level timing confirms that the original EditWordDocument POST remains open after its complete body arrives: request body complete at 0.002154 s, first response payload at 54.560037 s, a 54.557883-second server-side wait. The 1,166,820-byte response transfers in about 1.362 ms. This proves a long-lived XHR; the exact Word/COM event that releases it remains unresolved. No separate close-time POST appears in this captured stream; other workflows may differ.

Current conclusion: the custom register-changes prompt and long-lived XHR are confirmed. The response DOC is a rewritten OLE container (estimated 875,008 bytes versus 872,960 input; first-directory-sector pointer 1698 → 1702), strongly consistent with the Word operation completing before the response is released. The exact callback-to-response edge and the parent page's final Almas registration request remain open.

### Native bridge implementation checkpoint

- GET /?heartbeat now returns HTTP 200 with the captured body TickTack and Content-Type text/html; charset=ISO-8859-1.
- GET /?init=<digits>_<digits> returns the 994-byte init script byte-for-byte identical to capture stream 4 when port and parent origin match; only those two values are substituted.
- protocol.py has a bounded serializer for the observed response-word success envelope (application/msword, encryption=base64).
- create_bridge_server now separates allowed_origins (the local XHR Origin, captured as http://127.0.0.1:1984) from allowed_parent_origins (the Almas page origin derived from init Referer, captured as https://automation.bsi.ir).
- Python bridge workflow #42 (run 43709846976) passed all 45 tests. No production EditWordDocument handler, LibreOffice integration, or live Almas end-to-end test is claimed complete.


### Request/response DOC comparison

The packet-level document comparison (pcap workflow #4, run 43710628491, artifact 14159604189) found:

- Request wordBody decodes to 872,960 bytes, OLE Compound File.
- Response application/msword decodes to 874,957 captured bytes. The response has 17 TCP sequence gaps totaling 68 missing Base64 characters, all within the Base64 document value.
- The missing 68 Base64 characters represent 51 decoded bytes. Estimated complete response size is 875,008 bytes, exactly 2,048 bytes larger than the input and aligned to 512-byte sectors.
- Both files have 14 FAT sectors. The first-directory-sector pointer at OLE header offset 48 changes from 1698 in the request to 1702 in the response.
- The first differing byte is offset 48, before the first capture gap; the first approximately 49,041 decoded bytes are available for comparison and are not equal.

The response is therefore not a byte-for-byte echo. It is a rewritten/restructured legacy DOC container. Full-file hash equality cannot be claimed because 51 decoded response bytes were not captured.


### Public Invoke wrapper versus inner XML helper — correction from BPL export workflow

The BPL export/API trace confirms that the public TEmwatMethod.Invoke entry is 0x0046C9E0, shared by descendants at VMT slot +0x0C. Its body calls the 433-byte inner dictionary/XML helper at 0x0046C82C (callsite 0x0046CA67), then calls the subclass VMT slot +0x10 (callsite 0x0046CA88). TD32 labels are misleading here: 0x0046C82C is symbolized as Invoke and 0x0046C9E0 as Finalization, but export metadata and the executable call flow establish the wrapper/helper roles. The XML node construction and TXMLEmwatType serializer slot +0x54 belong to the inner helper.


## 8. Gap-aware PCAP confirmation of the returned document (2026-11-15)

A later analysis of `emwat.pcapng` (workflow run `43711788034`, artifact `14160597175`) reconstructed the `127.0.0.1:61189 ↔ 127.0.0.1:1984` exchange for `POST /?invoke=58351`.

The response is HTTP 200 and contains this redacted structure:

```xml
<response-word status="success">
  <return-types>
    <type mimetype="application/msword" encryption="base64">…</type>
  </return-types>
</response-word>
```

The `type` content decodes to an OLE Compound File / legacy DOC container. The request's `wordBody` also decodes to an OLE Compound File, but the intact captured prefixes differ at decoded byte offset 48, the CFB header's first-directory-sector pointer (request 1698; response 1702). Both report 14 FAT sectors.

The response capture has 17 TCP sequence gaps, each 4 bytes (68 missing capture bytes) within the Base64 document. Therefore the observed response decode is 874,957 bytes and incomplete; the analyzer estimates 875,008 complete bytes and a 2,048-byte increase over the 872,960-byte request document. These are estimates, not a verified full-file diff or response hash.

The request body completes at approximately 0.002154 s from capture start; the first response payload arrives at 54.560037 s. This proves a long request-to-response interval in this sample, but not which internal component accounts for it.

**Updated confidence:** the captured `EditWordDocument` response does return a Base64-encoded Word document with MIME type `application/msword`, and that returned container differs from the submitted `wordBody` in the intact captured prefix. This materially strengthens the close/finalization return-path model. It still does not prove that every session uses the same timing or that the response is emitted exclusively by a specific Word event.

Detailed measurements, limitations, and reproducibility are in [PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md](PCAP-EDITWORD-DOCUMENT-ROUNDTRIP.md).


## Run 125 — Word Fields collection and XML field helpers (2026-11-16 review)

Artifact emwat-word-lifecycle-analysis from run 43722990611 was re-opened to separate the editor's Word Fields path from the print-handler path.

### Word Fields enumeration

- TWordViwer.GetDocFieldIndex occupies 0x004C0550–0x004C1793 (0x1244 bytes).
- It obtains the Word document's Fields collection and reads its count through an interface call at slot +0x28.
- It enumerates entries through the collection's item accessor at slot +0x38, then reads field metadata and calls FindFieldInActivefields (0x004BC170) to match the Word-side field against the viewer's active-field list.
- The routine calls FillTextField (0x004BC980) and FillMSWFields (0x004C009C) as part of this resolution/collection process.
- FillMSWFields is called three times from GetDocFieldIndex and once from GetCaptionItemFont. It builds internal collections at viewer offsets +0xE8 and +0xEC, storing strings, flags, and associated field metadata. Exact record semantics remain unresolved.

This establishes that the Windows editor does not merely search bookmarks: it actively enumerates Word's Fields collection and builds a metadata/index representation. The Linux Writer compatibility layer must therefore inventory and eventually map Writer text fields as well as bookmarks, named ranges, content controls, and image anchors.

### Text/image helper separation

- TWordViwer.FillField (0x004BC2C4, 70 bytes) appends a string to an internal dynamic array at viewer offset +0x60. Its short body does not itself perform a Word COM field insertion.
- TWordViwer.FillTextField (0x004BC980, 264 bytes) reads values through an XML field interface (slot +0xB0) and conditionally delegates to FillImageField. It is used by GetXmlFieldInfo, GetDocFieldIndex, and FillImgFldsForPrint; it should not be interpreted as a simple one-line Word text setter.
- TWordViwer.FillImageField (0x004BC30C, 1,652 bytes) checks viewer/document state and XML-field attributes, then interacts with Word Field and image-related interfaces. The full image payload insertion and formatting semantics are not yet completely resolved.
- TWordViwer.FillMSWFields (0x004C009C, 592 bytes) is a field-metadata collection builder, not the same routine as the print handler's TEmwatDocPrintHandler.FillField.
- The separate print-handler FillField at 0x004A5F68 normalizes a string and writes it to its print-flow target; do not reuse that implementation as the editor's field-mapping contract.

### Linux implementation consequences

1. Keep WriterDocumentCatalog.text_fields as a first-class inventory; bookmark-only mapping would be incomplete.
2. Keep text and image field adapters separate.
3. Treat FillMSWFields' internal arrays as unresolved metadata until their element layout and call arguments are mapped.
4. Do not map any of the 180 request field IDs to a Writer element by name alone until a real anonymized template is available.
5. The installer archive inventory run 43810767154 found no Word-family template files, so template-level validation remains blocked on a representative Almas letter/template fixture.



## Run 126 — تکمیل مسیر Custom Document Properties و تشخیص نوع فیلد (2026-11-16)

Artifact اجرای `43811074616` (موفق؛ 41 فایل trace/disassembly) بررسی شد. این مرحله چند مرز مهم را دقیق‌تر کرد:

### تشخیص متن در برابر تصویر

- `TWordViwer.FillTextField` در `0x004BC980–0x004BCA87`، خودش متن را در Word نمی‌نویسد.
- این متد metadata فیلد XML را از interface slot `+0xB0` می‌خواند و MIME type را با `text/plain` مقایسه می‌کند.
- در صورت نبود metadata مناسب یا غیر `text/plain` بودن MIME type، مسیر را به `FillImageField` در `0x004BC30C` واگذار می‌کند.
- بنابراین نام FillTextField نباید به‌عنوان اثبات setter متنی تفسیر شود؛ این متد در این مسیر نقش dispatch/نوع‌سنجی متن در برابر تصویر دارد. نوشتن نهایی متن در مسیرهای دیگر باید جداگانه ردیابی شود.

### استخراج Custom Document Properties

- `TWordViwer.AddCustomDocPropertiesToDic` در `0x004D1454–0x004D1807` از مسیر `LoadDocument` فراخوانی می‌شود (callsite: `0x004B7994`).
- تابع یک collection از custom document properties را پیمایش می‌کند، نام propertyها را از رشته‌های هر عضو استخراج/تفکیک می‌کند و رکوردهای single/twin را برای دو dictionary در offsetهای viewer `+0x68` و `+0x6C` آماده می‌کند. trace بعدی نشان داد callهای مستقیم این تابع به helperهای generic `Remove` می‌رسند؛ مسیر درج نهایی هنوز جداگانه باید ردیابی شود.
- جزئیات دقیق قالب نام/مقدار و معنای همه فیلدهای رکورد هنوز به helperهای `0x004D531C` و `0x004D68D4` وابسته است؛ تا trace آن helperها کامل نشود، delimiter و قرارداد نهایی dictionary را قطعی اعلام نمی‌کنیم.
- این مسیر مستقل از bookmark inventory است. پس catalog لینوکس اکنون باید نام Custom Document Properties را نیز، بدون خواندن مقدارشان، فهرست کند.

### نقش GetDocFieldName در lifecycle

- `GetDocFieldName` در `0x004BB81C–0x004BC16F` روی مجموعه فیلدهای سند گردش می‌کند و برای هر عضو `GetDocFieldIndex` را فراخوانی می‌کند.
- در همین مسیر، اگر نام/شرط مشخصی در بررسی رشته‌ای برقرار باشد، `SilentSaveEmwatDoc` در `0x004D23D8` فراخوانی می‌شود؛ بنابراین silent-save یک fallback شرطی در منطق شناسایی فیلد است، نه اثبات یک callback عمومی برای هر بار بستن سند.
- این یافته با نتیجه قبلی سازگار است: مسیر نهایی ثبت سند به lifecycle و پاسخ XHR بلندمدت مرتبط است، اما هنوز نباید silent-save را معادل ثبت نهایی در Almas دانست.

### پیامد برای Writer

- catalog ساختاری اکنون نام‌های Custom Document Properties را کنار bookmark، named range، text field، section، table، frame و graphic object ثبت می‌کند.
- فقط نام propertyها خوانده می‌شوند؛ هیچ مقدار property، متن سند یا presentation فیلد در گزارش inventory خوانده نمی‌شود.
- تست UNO واقعی یک custom property ساختگی به سند اضافه می‌کند و حضور نام آن را در catalog بررسی می‌کند. این تست، قابلیت inventory را تأیید می‌کند، نه mapping نهایی 180 فیلد EMWAT به قالب واقعی نامه.


### قاعده نام‌گذاری فیلدهای امضا در GetDocFieldIndex

- پس از resolve کردن نام فیلد Word و تطبیق آن با active-field list از مسیر `FindFieldInActivefields` در `0x004BC170`، تابع `GetDocFieldIndex` نام حاصل را با regex زیر بررسی می‌کند: `^sign.*end[0-2]?[0-9]?`.
- در صورت تطبیق، مسیر log با متن `field[%d]: "%s" skiped by business.` اجرا می‌شود و شاخه پردازش عادی آن فیلد کنار گذاشته می‌شود.
- این regex از ابتدای نام شروع می‌شود و suffix عددی اختیاری محدود به الگوی 0 تا 29 را می‌پذیرد؛ چون انتهای رشته با `$` بسته نشده، وجود ادامه بعد از این الگو نیز از نظر regex مجاز است.
- این یک قاعده اختصاصی برای برخی فیلدهای sign/end است؛ هنوز نباید آن را معادل قرارداد کامل `signData` یا نحوه ادغام امضاها دانست.
- مرحله بعد، trace کردن helperهای `0x004D531C` و `0x004D68D4` و decode رشته‌های ثابت مربوط به delimiter و نام فیلدهاست. workflow جدید `analyze-word-custom-property-pipeline.yml` این تحلیل‌ها را موازی اجرا می‌کند.


### تکمیل trace: delimiter واقعی فیلدهای تکی و Twin

Artifact جدید `43812127854` delimiter ثابت در `0x004D1768` را به‌صورت Unicode برابر `†` (U+2020 DAGGER) decode کرد.

- `AddCustomDocPropertiesToDic` رشته نام هر Custom Document Property را با اولین `†` بررسی می‌کند.
- اگر دو سمت delimiter هر دو غیرخالی باشند، رکورد از نوع `TXmlWordConfigTwinField` ساخته می‌شود و دو بخش نام در دو عضو جداگانه رکورد ذخیره می‌شوند.
- اگر delimiter وجود نداشته باشد، یا یکی از دو سمت خالی باشد، مسیر به رکورد `TXmlWordConfigField` تکی برمی‌گردد.
- دو مجموعه داخلی viewer در offsetهای `+0x68` و `+0x6C` به‌ترتیب از نوع `TDictionary<UnicodeString,TXmlWordConfigField>` و `TDictionary<UnicodeString,TXmlWordConfigTwinField>` هستند. helperهای `0x004D531C` و `0x004D68D4` متدهای generic `Remove` همین دو دیکشنری‌اند؛ بنابراین آن‌ها setter یا درج‌کننده مستقیم نیستند.
- کد پایتون اکنون `parse_word_field_identifier` را دارد: اولین dagger را جدا می‌کند، twin را تشخیص می‌دهد و ورودی با سمت خالی را مانند مسیر single نگه می‌دارد. تست‌ها حالت single، twin، چند delimiter و delimiter ابتدا/انتها را پوشش می‌دهند.

### دو نام ثابت در مسیر GetDocFieldName

Decode رشته‌های ثابت نشان داد مقایسه‌های این مسیر شامل `RtlDate` و `Hidden_Customizable` هستند. در نتیجه، فراخوانی `SilentSaveEmwatDoc` در `GetDocFieldName` باید همچنان یک شاخه شرطی مرتبط با این نام‌ها تلقی شود؛ نام‌ها به‌تنهایی قرارداد ثبت یا ذخیره‌سازی Almas را ثابت نمی‌کنند.


### تکمیل مسیر نوشتن مقدار فیلد در Word

بازخوانی disassembly کامل `FillImageField` در `0x004BC30C` نشان داد نام این تابع گمراه‌کننده است و مسیر فقط درج تصویر نیست:

- در صورت فعال بودن flag داخلی `viewer+0xF0`، سه نام ویژه `LetterRegistrationDate`، `LetterRegistrationNo` و `ProduceDate` وارد مسیر آماده‌سازی/اصلاح مقدار می‌شوند.
- تابع ابتدا dictionary فیلدهای XML را بررسی می‌کند؛ log صریح آن می‌گوید مقدار یک فیلد می‌تواند در `CustomDocumentProperties[index]` ذخیره شود.
- مسیر جایگزین، مقدار را در ناحیه `Field.Result.Text` می‌نویسد؛ log صریح `field value stored on Field.Result.Text area.` این مقصد را تأیید می‌کند.
- پس از نوشتن در مسیر Field.Result.Text، کد وضعیت قفل فیلد را بررسی می‌کند و log `field locked.` دارد.
- در نتیجه، مدل مقصد فیلد در پیاده‌سازی Linux نباید فقط یک Writer text field باشد: دست‌کم مسیر Custom Document Property، مسیر نتیجه Text Field، و مسیر تصویر باید جداگانه قابل نمایش/آزمایش باشند.
- `FillTextField` همچنان نقش تشخیص metadata/MIME و dispatch را دارد؛ اما `FillImageField` در عمل بخشی از منطق عمومی مقداردهی فیلد را هم اجرا می‌کند. mapping هر 180 شناسه به مقصد مشخص همچنان به template واقعی و تکمیل trace وابسته است.


### Run 127 — lookup و به‌روزرسانی Custom Document Property (2026-11-16)

Artifact اجرای `43812565648` با موفقیت تکمیل شد و helperهای مقصد مقدار فیلد را مشخص‌تر کرد:

- `0x004D3DF8` متد `TDictionary<UnicodeString,TDocumentCProperty>.ContainsValue` است.
- `0x004D34B0` متد `TDictionary<UnicodeString,TDocumentCProperty>.SetItem` است.
- هر دو از `FillImageField` فراخوانی می‌شوند؛ بنابراین مسیر Custom Document Properties صرفاً inventory یا lookup نام نیست و مقدار رکورد `TDocumentCProperty` در dictionary به‌روزرسانی می‌شود.
- متن log `CustomDocumentProperties[%d]` با این مسیر dictionary-backed سازگار است؛ اما ترتیب indexها و قرارداد کامل رکورد `TDocumentCProperty` هنوز باید با helperهای سازنده و Word collection تطبیق داده شود.
- `0x004D1B30` طبق TD32 نام واقعی `ShowRecAndCcOptionForm` دارد و از `GetDocFieldName` فراخوانی می‌شود؛ این تابع را نباید field-name array یا silent-save helper فرض کرد.
- `0x0045644C` تابع `Emwatutils.FindWindowExtd` است، نه date formatter. در مسیر ویژه `FillImageField` برای سه شناسه `LetterRegistrationDate`، `LetterRegistrationNo` و `ProduceDate` به‌کار می‌رود؛ معنای دقیق transform آن هنوز باز است.

**اصلاح برداشت قبلی:** سه نام بالا special-case هستند، اما helper فراخوانی‌شده `FindWindowExtd` است؛ بنابراین ادعای «تاریخ‌فرمت‌کن» بودن آن حذف می‌شود تا رفتار تابع با trace کامل و call context ثابت شود.


### جزئیات الگوریتم FindWindowExtd در special-caseها

بازخوانی بدنه کامل `0x0045644C` نشان داد:

- ورودی رشته را کاراکتر به کاراکتر پیمایش می‌کند.
- جداکننده‌های `/` و `-` را از tokenها جدا کرده و tokenها و جداکننده‌ها را در دو فهرست نگه می‌دارد.
- سپس از انتهای فهرست به ابتدا حرکت می‌کند و رشته خروجی را از tokenها و جداکننده‌ها بازسازی می‌کند.
- بنابراین این helper یک parser/rebuilder رشته‌ای با ترتیب پیمایش معکوس است؛ احتمالاً برای اصلاح ترتیب اجزای مقدارهای دارای slash/hyphen استفاده می‌شود، اما هدف دقیق locale/نمایش از این trace به‌تنهایی ثابت نیست.
- در `FillImageField` فقط وقتی flag داخلی فعال است و شناسه یکی از سه فیلد ویژه باشد، این helper روی مقدار ورودی اعمال می‌شود. نباید آن را یک date formatter عمومی دانست.
