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
