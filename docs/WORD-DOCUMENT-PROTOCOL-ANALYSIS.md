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
