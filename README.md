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
- [نقشه پیاده‌سازی بومی لینوکس و مسیرهای موازی](docs/LINUX-NATIVE-IMPLEMENTATION-PLAN.md)
- [اعتبارسنجی runtime نسخه Windows با Winux/Wine](docs/WINUX-RUNTIME-VALIDATION.md)
- [تحلیل گردش‌کار واقعی EMWAT در الماس گام](docs/PRODUCT-WORKFLOW-ANALYSIS.md)
- [تحلیل connector و ساختار XML گردش‌کار Word](docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md)
- [تحلیل ایستای چرخه Word و اختلاف VMT/TD32](docs/WORD-LIFECYCLE-STATIC-TRACE.md)
- [تحلیل تایمر AutoSave و مسیر SilentSave](docs/AUTOSAVE-TIMER-AND-SILENT-SAVE-TRACE-2026-11-17.md)
- [اصلاح شواهد راه‌اندازی Word و گردآوری فیلدها](docs/WORD-LOAD-AND-FIELD-COLLECTION-EVIDENCE-CORRECTION-2026-11-17.md)
- [زنجیره انتظار بستن Word، بازیابی دوره‌ای و پاسخ HTTP](docs/WORD-CLOSE-WAIT-AND-RESPONSE-CORRELATION-2026-11-17.md)
- [طراحی snapshot بازیابی بومی لینوکس](docs/LINUX-NATIVE-RECOVERY-SNAPSHOT-DESIGN-2026-11-17.md)
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
- ابزار [ردیابی دسترسی به فیلدهای instance در TD32](tools/scan_td32_instance_field_refs.py) برای یافتن read/writeهای candidate روی offsetهای `TWordViwer`

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

در شاخه فعلی، یک بسته Python اولیه در مسیر `python/` اضافه شده است. لایه انتقال HTTP بدنه را به‌صورت bytes خام نگه می‌دارد؛ parser و dispatcher در ماژول‌های جداگانه قرار دارند. parser پوسته تأییدشده `emwat → method → param` را می‌خواند و dispatcher فقط handlerهای صریحاً ثبت‌شده را اجرا می‌کند. schema محتوای `EditWordDocument` و پاسخ نهایی هنوز کامل نیست.

تست‌های واحد در `python/tests/test_bridge.py` و workflow مستقل `Python bridge transport` در GitHub Actions قرار دارند. این milestone فقط foundation انتقال است و هنوز با وب‌اپ الماس گام یا Word/LibreOffice یکپارچه نیست.

**CI verification (latest):** workflow `Python bridge transport` run #20 (`43592721635`) passed all 24 tests on commit `2fa217ae83f33b80a7799ede4c75f2cc58b40d76`. This verifies only the transport, envelope parser and explicit dispatcher—not compatibility with the production Almas Gam origin or the full Word workflow.

### XML protocol foundation

The Python package now contains a conservative parser for the runtime-confirmed `emwat version="1.0" → method class → param name` envelope (`python/src/emwat_linux/protocol.py`) and an explicit allowlisted dispatcher (`python/src/emwat_linux/dispatcher.py`). Unknown method classes return HTTP 501; malformed envelopes return HTTP 400. Method class names are never dynamically imported. No `EditWordDocument` handler or fabricated success response is registered yet.

The loopback transport is hardened with IPv4-loopback-only binding, Host-header validation, required exact allowlisted Origin by default, bounded request/response bodies, socket read timeouts, duplicate Content-Length rejection, and sanitized errors. CI run #20 passes all 24 tests. This remains a transport/protocol foundation, not a usable Almas Gam connector.

**Latest CI hardening:** Python bridge transport run #22 (`43593083176`) passed all 27 tests on commit `22a803912b0fa92c3bb5537fb1f0c7952fda7615`. Additional tests cover Host header path injection, duplicate Content-Length and non-decimal Content-Length. The listener now rejects malformed Host values and strict-invalid HTTP framing before dispatch.

### Application composition factory

`python/src/emwat_linux/application.py` now provides `create_bridge_server(...)`, wiring the loopback transport, XML parser and explicit method registry. The caller must provide the exact allowed Origin list and explicit method handlers; nothing is implicitly enabled. An integration test exercises the complete local HTTP → XML parser → registered handler → HTTP response path. Python bridge workflow run #24 (`43593185429`) passed all 29 tests on commit `27986ee96b45009283cd96eecde95110e1b9e448`. The only registered method in the integration test is a test fixture, not the real EMWAT document handler.


### Parallel implementation progress (2026-11-15)

The native bridge now includes the observed Agent liveness route GET /?heartbeat (HTTP 200, empty response body) with a regression test. A separate office-independent document-session state machine is available at python/src/emwat_linux/sessions.py; it distinguishes office-engine Save from close-time finalization and supports safe idempotent return. Tests were added for lifecycle transitions and heartbeat behavior. These newest commits are not yet represented by a verified CI run, and no production Almas Gam handler or LibreOffice integration is claimed.


## Build and test

See [docs/BUILD-AND-TEST.md](docs/BUILD-AND-TEST.md) for reproducible build and test commands for the native image/scanner core, Python bridge, and LibreOffice UNO integration suite.


## Reverse-engineering notes

- [BPL VMT and TD32 method-target reconciliation](docs/BPL-VMT-METHOD-TARGET-RECONCILIATION-2026-11-17.md)
- [Word COM event-sink registration and save behavior](docs/WORD-COM-EVENT-SINK-REGISTRATION-2026-11-17.md)
- [AutoSave settings and registry contract](docs/AUTOSAVE-SETTINGS-REGISTRY-CONTRACT-2026-11-17.md)
