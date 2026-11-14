# EMWAT-Linux

بازسازی بومی EMWAT برای Linux با هدف حفظ قابلیت‌ها و گردش‌کارهای واقعی نسخه Windows.

> نسخه نهایی قرار نیست با Wine اجرا شود. فایل‌های Windows فقط مرجع تحلیل و سازگاری هستند.

## کاربرد واقعی و هدف پروژه

EMWAT واسط محلی بین اتوماسیون تحت وب الماس گام و برنامه‌های دسکتاپ کاربر است. گردش‌کار اصلی شناخته‌شده، دریافت اطلاعات و قالب نامه از الماس گام، بازکردن Word برای تکمیل/ویرایش نامه و بازگرداندن فایل پس از پایان کار به همان سامانه است. بعضی نامه‌ها نیز کاملاً تصویری‌اند؛ بنابراین قابلیت‌های اسکن و پردازش تصویر در دامنه پروژه باقی می‌مانند.

جزئیات تأییدشده، شواهد فنی، موارد نامشخص و نقشه راه بازتنظیم‌شده در [تحلیل گردش‌کار واقعی EMWAT](docs/PRODUCT-WORKFLOW-ANALYSIS.md) ثبت شده‌اند.

## وضعیت فعلی

تحلیل اولیه فایل‌های اجرایی و گزارش‌های رشته‌ای انجام شده است. شواهد فعلی نشان می‌دهند EMWAT از یک سرویس HTTP محلی مبتنی بر Indy استفاده می‌کند؛ Agent به سرویس روی localhost heartbeat می‌فرستد و یک bridge جاوااسکریپت پیام‌ها را از طریق HTTP POST به سرویس محلی منتقل می‌کند. جزئیات کامل API، دیتابیس و گردش‌کارها هنوز در حال بررسی‌اند.

گزارش کامل وضعیت، شواهد، موارد نامشخص و گام‌های بعدی در این فایل نگهداری می‌شود:

- [گزارش وضعیت و نقطه ادامه پروژه](docs/PROJECT-STATUS.md)
- [تحلیل گردش‌کار واقعی EMWAT در الماس گام](docs/PRODUCT-WORKFLOW-ANALYSIS.md)
- [تحلیل connector و ساختار XML گردش‌کار Word](docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md)
- [تحلیل سرویس HTTP محلی و bridge](docs/HTTP-LOCAL-API-ANALYSIS.md)
- [تحلیل Import Table و وابستگی‌های Windows](docs/IMPORT-TABLE-ANALYSIS.md)
- [تحلیل Office Automation و COM](docs/OFFICE-COM-ANALYSIS.md)
- [تحلیل COM و PE Resourceهای استخراج‌شده](docs/RESOURCE-ANALYSIS.md)
- [تحلیل ساختار فرم تنظیمات چاپ Word](docs/WORD-PRINT-OPTION-DFM.md)
- [تحلیل فرم پیش‌نمایش اسکن و ابزارهای تصویر](docs/SCAN-PREVIEW-DFM.md)
- [تحلیل فرم اصلی مدیریت و ویرایش تصاویر](docs/IMAGE-TOOLS-DFM.md)
- [تحلیل ویرایشگر ساده تصویر و مقایسه سه فرم](docs/SIMPLE-IMAGE-EDITOR-DFM.md)
- [نقشه وابستگی‌های ImageGear و ImageEn](docs/Imaging-Dependency-Map.md)
- [گراف فراخوانی‌های تصویر و اسکن](docs/IMAGE-CALL-GRAPH.md)
- [تحلیل دقیق APIهای ImageGear](docs/GEAR-API-CALLS.md)
- [تحلیل قرارداد انتخاب اسکنر و رابط‌های callback](docs/SCANNER-INTERFACE-ANALYSIS.md)
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

## نقطه ادامه پروژه

با توجه به کاربرد واقعی که از کاربر تأیید شده، اولویت بعدی دیگر صرفاً توسعه موتور اسکن نیست. ابتدا باید قرارداد ارتباطی bridge مرورگر و سرویس Windows، dispatch متدها و انتقال فایل را از روی BPL و یک سناریوی runtime استخراج کنیم. سپس یک نمونه انتها‌به‌انتها برای نامه متنی با LibreOffice بسازیم. موتور تصویر و اسکن حفظ می‌شود و پس از روشن‌شدن گردش‌کار نامه‌های تصویری تکمیل خواهد شد.

برای ترتیب دقیق کارها و مواردی که هنوز نیازمند آزمایش هستند، [تحلیل گردش‌کار واقعی EMWAT](docs/PRODUCT-WORKFLOW-ANALYSIS.md) و [گزارش وضعیت پروژه](docs/PROJECT-STATUS.md) را ببینید.

## Session continuity

For the current project decisions, implementation boundaries, and next-session checklist, see [docs/SESSION-HANDOFF.md](docs/SESSION-HANDOFF.md).


## پل بومی HTTP در لینوکس — لایه انتقال اولیه

در شاخه فعلی، یک بسته Python اولیه در مسیر `python/` اضافه شده است. این لایه فقط انتقال HTTP محلی را فراهم می‌کند: bind اجباری روی IPv4 loopback، endpoint سلامت `/healthz`، پذیرش POST روی ریشه، حفظ بدنه به‌صورت bytes و بدون parse/تغییر، محدودیت اندازه بدنه، رد Originهای خارج از allowlist پیکربندی‌شده، و پاسخ خطای sanitize‌شده. قرارداد XML/dispatcher عمداً هنوز در این لایه پیاده نشده است؛ زیرا نام تگ پارامتر و schema کامل response نهایی هنوز اثبات نشده‌اند.

تست‌های واحد در `python/tests/test_bridge.py` و workflow مستقل `Python bridge transport` در GitHub Actions قرار دارند. این milestone فقط foundation انتقال است و هنوز با وب‌اپ الماس گام یا Word/LibreOffice یکپارچه نیست.


**CI verification:** workflow `Python bridge transport` run `43592145701` completed successfully for commit `c705ed34ad9a9e87b42d7e2d85d3aa60aea83815`. The transport response now echoes `Access-Control-Allow-Origin` only for an exact configured Origin (never `*`), so a browser can read an allowed origin's response. The initial CI failures exposed two setup/fixture issues (unnecessary setuptools install in CI; test fixture larger than its configured cap); both were corrected before the successful run. This does not validate compatibility with the Almas Gam production origin or legacy XML schema.

### XML protocol foundation

The Python package now contains a conservative parser for the runtime-confirmed `emwat version="1.0" → method class → param name` envelope (`python/src/emwat_linux/protocol.py`) and an explicit allowlisted dispatcher (`python/src/emwat_linux/dispatcher.py`). Unknown method classes return HTTP 501; malformed envelopes return HTTP 400. Method class names are never dynamically imported. No `EditWordDocument` handler or fabricated success response is registered yet.

The loopback transport is hardened with IPv4-loopback-only binding, Host-header validation, required exact allowlisted Origin by default, bounded request/response bodies, socket read timeouts, duplicate Content-Length rejection, and sanitized errors. CI run #20 passes all 24 tests. This remains a transport/protocol foundation, not a usable Almas Gam connector.
