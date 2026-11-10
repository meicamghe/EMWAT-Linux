# EMWAT-Linux

بازسازی بومی EMWAT برای Linux با هدف حفظ قابلیت‌ها و گردش‌کارهای واقعی نسخه Windows.

> نسخه نهایی قرار نیست با Wine اجرا شود. فایل‌های Windows فقط مرجع تحلیل و سازگاری هستند.

## وضعیت فعلی

تحلیل اولیه فایل‌های اجرایی و گزارش‌های رشته‌ای انجام شده است. شواهد فعلی نشان می‌دهند EMWAT از یک سرویس HTTP محلی مبتنی بر Indy استفاده می‌کند؛ Agent به سرویس روی localhost heartbeat می‌فرستد و یک bridge جاوااسکریپت پیام‌ها را از طریق HTTP POST به سرویس محلی منتقل می‌کند. جزئیات کامل API، دیتابیس و گردش‌کارها هنوز در حال بررسی‌اند.

گزارش کامل وضعیت، شواهد، موارد نامشخص و گام‌های بعدی در این فایل نگهداری می‌شود:

- [گزارش وضعیت و نقطه ادامه پروژه](docs/PROJECT-STATUS.md)
- [تحلیل سرویس HTTP محلی و bridge](docs/HTTP-LOCAL-API-ANALYSIS.md)
- [تحلیل Import Table و وابستگی‌های Windows](docs/IMPORT-TABLE-ANALYSIS.md)
- [تحلیل Office Automation و COM](docs/OFFICE-COM-ANALYSIS.md)
- [تحلیل COM و PE Resourceهای استخراج‌شده](docs/RESOURCE-ANALYSIS.md)
- [تحلیل ساختار فرم تنظیمات چاپ Word](docs/WORD-PRINT-OPTION-DFM.md)
- [تحلیل فرم پیش‌نمایش اسکن و ابزارهای تصویر](docs/SCAN-PREVIEW-DFM.md)
- [تحلیل فرم اصلی مدیریت و ویرایش تصاویر](docs/IMAGE-TOOLS-DFM.md)
- [تحلیل ویرایشگر ساده تصویر و مقایسه سه فرم](docs/SIMPLE-IMAGE-EDITOR-DFM.md)
- ابزار [استخراج GUID/ProgID و Resourceها](tools/EMWAT-COM-Resource-Analyzer.py)

## گزارش‌ها و فایل‌های مرجع موجود

- `EMWAT_Extracted.zip` — آرشیو فایل‌های استخراج‌شده برای تحلیل
- `EmwatService.exe-strings.txt`
- `EmwatAgent.exe-strings.txt`
- `EmwatMethods.bpl1-strings.txt`
- `EMWAT-Analysis-Results.txt` — خروجی فیلترشده و تجمیع‌شده
- `EMWAT-Import-Report.txt` — خروجی Import Table سه فایل اصلی

گزارش‌های رشته‌ای فقط سرنخ هستند؛ وجود نام یک کلاس یا کتابخانه به‌تنهایی فعال‌بودن یک قابلیت را ثابت نمی‌کند.

## اصول توسعه

1. هدف، نسخه مستقل و بومی Linux است؛ Wine بخشی از راهکار نهایی نیست.
2. پیش از پیاده‌سازی، API، دیتابیس، فایل‌ها، فرمول‌ها و گردش‌کارهای نسخه اصلی مستند شوند.
3. Python گزینه اولیه برای پیاده‌سازی است؛ انتخاب معماری نهایی پس از تکمیل تحلیل انجام می‌شود.
4. LibreOffice برای سازگاری اسناد و صفحه‌گسترده‌ها بررسی می‌شود؛ سازگاری باید با تست واقعی تأیید شود.
5. هیچ موتور دیتابیسی تا زمان شناسایی شواهد واقعی به‌عنوان انتخاب نهایی تثبیت نشود.
6. فایل‌های اجرایی، داده‌های مشتریان، کلیدها و اطلاعات محرمانه نباید در مخزن عمومی قرار بگیرند. گزارش‌های خام نیز پیش از commit باید از نظر اطلاعات حساس بازبینی شوند.

## نقطه شروع جلسه بعد

ابتدا [گزارش وضعیت پروژه](docs/PROJECT-STATUS.md)، [تحلیل HTTP](docs/HTTP-LOCAL-API-ANALYSIS.md)، [تحلیل Importها](docs/IMPORT-TABLE-ANALYSIS.md) و [تحلیل Office/COM](docs/OFFICE-COM-ANALYSIS.md) را بخوان. Word/Excel Automation تأیید شده؛ گزارش COM/Resource Analyzer تولید و بررسی شده است؛ یافته‌ها در [تحلیل Resourceها](docs/RESOURCE-ANALYSIS.md) ثبت شده‌اند. فرم تنظیمات چاپ Word و هر سه فرم اسکن/تصویر به‌صورت کامل decode شده‌اند؛ گام بعدی ردیابی handlerهای تصویر در BPL و تدوین specification ماژول بومی است.
