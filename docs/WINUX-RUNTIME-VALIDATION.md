# EMWAT runtime validation under Winux/Wine

آخرین به‌روزرسانی: 2026-11-15

## هدف و محدوده

این سند یافته‌های اجرای واقعی نسخه Windows برنامه EMWAT در prefix مدیریت‌شده توسط Winux Engine را ثبت می‌کند. این آزمایش‌ها برای شناخت رفتار نسخه اصلی و تعیین نیازمندی‌های بازسازی بومی EMWAT-Linux هستند؛ **راهکار نهایی پروژه اجرای EMWAT با Wine نیست**.

نتایج این سند از خروجی فرمان‌ها و لاگ‌هایی است که کاربر در 2026-11-14 و 2026-11-15 ارائه کرده است. این نتایج را نباید با تحلیل ایستا یا تست CI پل Python یکی دانست.

## محیط آزمایش

- میزبان: Ubuntu در VMware.
- مسیر prefix: `~/.local/share/winux/prefixes/emwat`.
- فایل نصب استفاده‌شده: `/home/m/EmwatInstaller.exe`.
- نصب از طریق Winux Engine انجام شده است، نه اجرای مستقیم Wine از shell.
- فرمان توسعه‌ای استفاده‌شده:

```bash
cd ~/Winux
PYTHONPATH=src python3 -m winux install \
  /home/m/EmwatInstaller.exe \
  --prefix emwat \
  --timeout 3600
```

- گزارش نصب مورخ 2026-11-15:
  `~/.local/share/winux/logs/installations/20261115T061514Z-0a30f49e9ffc.log`
- شناسه نصب: `0a30f49e9ffc`.
- وضعیت ثبت‌شده توسط Winux: `SUCCESS`؛ وضعیت verification برابر `PENDING`.
- معماری فایل نصب شناسایی‌شده: x86؛ معماری برنامه در آن مرحله ناشناخته بود.
- نصب‌کننده اجزایی با نام‌های `EmwatAgent.exe`، `EmwatService.exe`، `GAMPrinterSetup.exe`، `zvprt5_setup.exe` و `AutoRegister.exe` را اجرا کرده است.
- هشدارهای ثبت‌شده شامل نبود `ntlm_auth`، پیام Wise درباره `Billboard` و پیام‌های Wine هستند. این هشدارها به‌تنهایی اثبات خرابی سرویس نیستند.

## یافته‌های runtime تأییدشده

### 1. اجزای نصب‌شده

Winux Application Discovery دو مورد را در prefix شناسایی کرده است:

- **Emwat Service** — نسخه `6.3.7.10251`، ناشر `Gamelectronics Co.`.
- **GAM Virtual Printer** — شناسه رجیستری `zvprt50`؛ executable و اطلاعات نسخه از مسیر discovery قابل تعیین نبودند.

اطلاعات ثبت‌شده برای Emwat Service:
- Product/Uninstall key: `{090A3899-3DE7-465D-877A-29B20BA94A23}`.
- مسیر نصب: `C:\\ProgramData\\Gamelectronics\\Emwat Service`.
- executable: `EmwatService.exe`.
- uninstall از طریق MSI ثبت شده است.

برای GAM Virtual Printer مسیر uninstall ثبت‌شده `C:\\Program Files\\zvprt50\\uninstall.exe` است؛ وجود این مقدار رجیستری به‌تنهایی عملکرد چاپگر را ثابت نمی‌کند.

### 2. فرایندهای فعال

در زمان مشاهده، دو فرایند Wine مربوط به EMWAT فعال بودند:

- `EmwatAgent.exe`، PID مشاهده‌شده `8767`.
- `EmwatService.exe`، PID مشاهده‌شده `8772`.

هر دو با کاربر عادی سیستم (`m`) اجرا شده بودند، نه root. مسیر اجرایی گزارش‌شده در `/proc/<pid>/exe` به Wine اشاره داشت و command line مسیر Windows هر executable را نشان می‌داد.

در همان زمان:
- `winux process list` فرایند ثبت‌شده‌ای نشان نداد.
- `winux service list` سرویس مدیریت‌شده‌ای نشان نداد.

بنابراین اجرای فرایندهای EMWAT مشاهده شده، اما مدیریت چرخه عمر آن‌ها توسط ProcessManager یا ServiceManager خود Winux هنوز برقرار/تأیید نشده است. این مشاهده به‌تنهایی به معنای نیاز به ثبت آن‌ها به‌عنوان سرویس Linux نیست.

### 3. سرویس HTTP محلی روی پورت 1984

آزمایش socket:

```
LISTEN 127.0.0.1:1984
process: wineserver
```

آزمایش درخواست:

```
curl -i --max-time 5 http://127.0.0.1:1984/
```

پاسخ مشاهده‌شده:

```http
HTTP/1.1 200 OK
Connection: close
Content-Length: 0
Set-Cookie: IDHTTPSESSIONID=; Expires=Sat, 23-Dec-1899 03:30:00 GMT
```

نتیجه دقیق:
- یک listener روی IPv4 loopback و پورت 1984 وجود داشته است.
- درخواست GET به مسیر ریشه پاسخ HTTP 200 گرفته است.
- پاسخ بدنه نداشته است.
- مالک socket در خروجی `ss`، فرایند `wineserver` گزارش شده است؛ بنابراین این خروجی PID دقیق executable ویندوزیِ پذیرنده درخواست را مشخص نمی‌کند.

**محدودیت:** پاسخ GET به مسیر `/` فقط دسترسی‌پذیری HTTP را در همان لحظه ثابت می‌کند. این آزمایش heartbeat، init، POST، dispatch متدهای XML، صحت CORS/Origin، یا عملکرد EditWordDocument را اعتبارسنجی نکرده است. HTTP 200 خالی نیز به‌تنهایی به معنی پاسخ موفق به یک عملیات EMWAT نیست.

### 4. لاگ‌های Service و Agent

فایل لاگ Service:

`drive_c/users/m/AppData/Local/Temp/emwat-diag/MainSvcLogger.log`

خطوط مشاهده‌شده:

```
info - 2026/11/14-14:41:50:168 656, Application: Started.
info - 2026/11/14-14:41:50:188 656, Application: Listenning on port 1984
info - 2026/11/15-10:16:14:603 660, Application: Started.
info - 2026/11/15-10:16:14:628 660, Application: Listenning on port 1984
```

فایل لاگ Agent:

`drive_c/users/m/AppData/Local/Temp/emwat-diag/AgentLog.log`

خط مشاهده‌شده:

```
11/15/2026 10:16:14 AM i: >> Start Agent
```

این خطوط شروع Service، گوش‌دادن آن روی پورت 1984 و شروع Agent را در زمان‌های ثبت‌شده تأیید می‌کنند. هنوز heartbeat موفق Agent، پیام‌های dispatch، یا تعامل کاربردی Agent با وب‌اپ از این لاگ‌ها اثبات نشده است.

### 5. وضعیت GAM Virtual Printer و CUPS

خروجی CUPS:

```
scheduler is running
no system default destination
lpstat: No destinations added.
```

پس CUPS روی میزبان فعال بوده، اما هیچ queue چاپی در آن زمان تعریف نشده بود.

فایل‌های مرتبط پیدا شده در prefix:

- `drive_c/windows/system32/winzvprt5.sys`
- `drive_c/windows/system32/zvprt5.ini`
- `drive_c/windows/system32/spool/drivers/x64/zvprt1.gpd`

محتوای غیرحساس قابل مشاهده از INI:

```ini
[setup]
installdir=C:\\Program Files\\zvprt50\\
DateTime=2026:11:15 09:45:26
```

همچنین فایل‌های چاپ Wine مانند `winprint.dll` و `wineps.drv` در prefix وجود دارند.

نتیجه:
- شواهدی از کپی‌شدن/نصب فایل‌های مرتبط با GAM printer در prefix وجود دارد.
- در این آزمایش هیچ CUPS queueای وجود نداشته است.
- وجود `.sys` و `.gpd` اثبات نمی‌کند driver در Windows spooler شبیه‌سازی‌شده Wine ثبت شده یا چاپ واقعی انجام می‌دهد.
- فایل `.sys` یک driver در سطح Windows است؛ سازگاری آن با Wine یا امکان جایگزینی آن با CUPS هنوز آزمایش نشده است.
- نبود فایل `unidrv.dll` در جست‌وجوی قبلی مشاهده شده، اما به‌تنهایی علت قطعی شکست چاپ نیست.

**وضعیت چاپگر: نصب فایل‌ها مشاهده شده؛ ثبت queue، enumeration توسط EMWAT، چاپ آزمایشی و دریافت خروجی هنوز تأیید نشده‌اند.**

## ارتباط این یافته‌ها با طراحی بومی Linux

1. سرویس محلی loopback بخشی از قرارداد سازگاری است؛ پورت 1984 و رفتار HTTP باید در specification پروتکل لحاظ شوند.
2. پورت نباید به‌صورت عمومی روی همه interfaceها باز شود. پیاده‌سازی Linux باید bind محدود به loopback، اعتبارسنجی Host و Origin، محدودیت اندازه درخواست و timeout داشته باشد.
3. Agent و Service دو نقش اجرایی جدا هستند. در بازسازی بومی باید مسئولیت heartbeat، سلامت سرویس، startup و recovery هرکدام از روی رفتار واقعی مشخص شود؛ ادغام آن‌ها بدون شواهد توصیه نمی‌شود.
4. نصب‌کننده Windows اجزای Service، Agent و Virtual Printer را نصب/اجرا می‌کند. نصب موفق این اجزا به معنای معادل‌بودن آن‌ها در Linux نیست.
5. چاپگر GAM را باید به‌عنوان یک زیرسامانه مستقل تحلیل کرد: قرارداد ورودی/خروجی، نام queue، تولید فایل، metadata چاپ، و وابستگی‌های Windows باید جداگانه استخراج شوند. CUPS صرفاً زیرساخت چاپ میزبان است و جایگزین خودکار driver اختصاصی GAM نیست.
6. تست نهایی محصول باید از تست transport جدا باشد: health، heartbeat، init، POST واقعی XML، dispatch، round-trip پاسخ به browser، بازشدن سند، ذخیره/بستن و چاپ هرکدام آزمون مستقل لازم دارند.

## ماتریس شواهد

| موضوع | وضعیت | شاهد | آنچه هنوز ثابت نشده |
|---|---|---|---|
| نصب از طریق Winux | تأییدشده | install record = SUCCESS | عملکرد کامل همه اجزا |
| Emwat Service | اجرا/شروع تأییدشده | process و log | همه عملیات کاربردی |
| Emwat Agent | شروع تأییدشده | process و AgentLog | heartbeat موفق و تعامل با browser |
| Listener پورت 1984 | تأییدشده | `ss` و HTTP GET 200 | API کامل و POST واقعی |
| HTTP root | پاسخ 200 خالی | `curl` | معنای کاربردی پاسخ |
| CUPS | scheduler فعال، بدون queue | `lpstat -t` | چاپ از EMWAT |
| GAM driver files | وجود فایل‌ها تأییدشده | `.sys`, `.ini`, `.gpd` | ثبت و کارکرد driver |
| Word/Almas end-to-end | نامشخص در این آزمایش | هیچ تست جدیدی انجام نشده | بازشدن/بازگشت واقعی سند |

## آزمایش‌های بعدی پیشنهادی

به ترتیب و بدون ثبت داده محرمانه:

1. از مرورگر، یک سناریوی آزمایشی در سامانه انجام و فقط metadata درخواست به loopback ثبت شود: method، path، query، Origin، Content-Type، اندازه بدنه و status؛ نه Cookie، token، متن نامه یا payload تصویری.
2. رفتار `?heartbeat` و `?init` را جداگانه ثبت کن؛ فقط وجود شاخه‌های static آن‌ها از قبل معلوم است و پاسخ runtime آن‌ها هنوز مشخص نیست.
3. یک POST کنترل‌شده از همان origin مجاز و با envelope آزمایشی بی‌خطر بررسی شود؛ از ارسال payload ساختگی به متد واقعی و تغییر داده سازمانی خودداری شود.
4. در محیط آزمایشی، بررسی شود آیا Agent بعد از startup به `/?heartbeat` درخواست می‌فرستد و رفتار آن هنگام خاموش‌شدن Service چیست.
5. وضعیت GAM printer در فهرست چاپگرهای Windows/Wine و خروجی چاپ واقعی بررسی شود؛ سپس امکان نگاشت امن به CUPS ارزیابی گردد.
6. workflow کامل نامه متنی با یک سند آزمایشی و بدون اطلاعات محرمانه از بازشدن تا بستن/بازگشت بررسی شود.

## محدودیت و محرمانگی

- این سند فقط خروجی‌های غیرحساس و شواهدی را که در جلسه ارائه شده‌اند ثبت می‌کند.
- هیچ محتوای نامه، تصویر، امضا، Cookie، token، credential یا HAR خام در این سند قرار نگرفته است.
- نتایج وابسته به همان prefix، میزبان و زمان آزمایش‌اند؛ برای تعمیم به نسخه‌های دیگر باید تکرار شوند.
- Wine صرفاً ابزار آزمایش رفتار نسخه Windows است و جزء معماری نهایی EMWAT-Linux نیست.

## تکمیل آزمایش HTTP و بررسی رشته‌های اجرایی — 2026-11-15

### 1. بررسی متدهای HTTP در مسیر ریشه

با سرویس فعال، چهار درخواست بدون payload کاربردی به مسیر ریشه پورت 1984 ارسال شد:

| متد | مسیر | نتیجه مشاهده‌شده |
|---|---|---|
| GET | `/` | `200 OK`، بدنه خالی، header کوکی `IDHTTPSESSIONID` |
| HEAD | `/` | `200 OK`، بدنه خالی، header کوکی `IDHTTPSESSIONID` |
| OPTIONS | `/` | `200 OK`، بدنه خالی؛ کوکی در خروجی مشاهده نشد |
| POST | `/` | `200 OK`، بدنه خالی، header کوکی `IDHTTPSESSIONID` |

Listener همچنان روی `127.0.0.1:1984` بود و `ss` مالک socket را `wineserver` گزارش کرد.

**تفسیر محدود:** این آزمایش فقط پاسخ‌گویی مسیر ریشه به چهار متد را ثابت می‌کند. POST بدون envelope معتبر و بدون endpoint/method واقعی، آزمون dispatch نیست. پاسخ 200 خالی می‌تواند از handler عمومی یا پیش‌فرض ناشی شده باشد. این خروجی‌ها پشتیبانی CORS، اجرای متدهای EMWAT، parse شدن body یا سازگاری API را ثابت نمی‌کنند.

### 2. رشته‌های استخراج‌شده از فایل‌های اجرایی

هر دو فایل `EmwatAgent.exe` و `EmwatService.exe` در مسیر نصب‌شده با استخراج رشته‌های Unicode و narrow بررسی شدند.

**رشته‌های EmwatService.exe:**
- نمادها و نوع‌های Indy HTTP server/session دیده شدند: `IdCustomHTTPServer`، `TIdHTTPRequestInfo`، `TIdHTTPResponseInfo`، `TIdHTTPSession`، `TIdHTTPCreateSession`، `TIdHTTPCreatePostStream` و `TIdHTTPDoneWithPostStream`.
- نام کوکی session: `IDHTTPSESSIONID`.
- رشته‌های HTTP شامل `HTTP/1.1`، `X-HTTP-Method`، `X-HTTP-Method-Override`، `Service Unavailable` و `HTTP version not supported`.
- رشته خطای bind پورت هشدار می‌دهد که EMWAT از قبل اجرا نباشد و پورت 1984 آزاد باشد.
- marker خاتمه سرویس: `{2EC42BF4-EA08-4476-AB86-466763F80E9A}_TERMINATE_EM_SERVICE_`.

**رشته‌های EmwatAgent.exe:**
- رشته‌های `LOCALHOST` و `127.0.0.1` وجود دارند.
- پیام‌های خطای مرتبط با Word: `Error on connect to MS-Word. Exception:`، `Can not open document.` و `Error on insert sign to word document. Exception:`.
- رشته‌های RTTI/symbol مربوط به `TLoginCredentialService` وجود دارند؛ این فقط وجود یک abstraction مرتبط با credential در binary را نشان می‌دهد و جزئیات عملکرد یا جریان داده را مشخص نمی‌کند.
- ارجاع به `AgentLog.log` و `EmwatService.exe` نیز وجود دارد.

**فایل‌های پیکربندی:** در مسیرهای جست‌وجوشده زیر ProgramData و AppData فایلی با پسوندهای `.config`، `.json`، `.xml` یا `.ini` که نام آن شامل Emwat باشد پیدا نشد. این نتیجه فقط به همان مسیرها و پسوندهای جست‌وجوشده محدود است.

### 3. ارزش این شواهد برای EMWAT-Linux

- وجود نمادهای Indy در Service با معماری HTTP server محلی که در تحلیل ایستا شناسایی شده بود سازگار است.
- Agent مسیرهای خطای مشخصی برای اتصال به MS Word، بازکردن سند و درج امضا دارد؛ اما strings به‌تنهایی ثابت نمی‌کنند این عملیات در نشست فعلی اجرا یا موفق شده‌اند.
- وجود `TLoginCredentialService` باید در تحلیل بعدی دنبال شود؛ از آن نمی‌توان نتیجه گرفت credentialها کجا ذخیره یا چگونه منتقل می‌شوند.
- marker خاتمه سرویس یک سرنخ برای تحلیل lifecycle است، اما هنوز نباید به‌عنوان API عمومی یا فرمان قابل فراخوانی استفاده شود.

### 4. آزمایش‌های بعدی

1. درخواست‌های بی‌خطر GET به `/?heartbeat` و `/?init` را جداگانه بررسی و status/header/body پاک‌سازی‌شده را ثبت کن.
2. handler مسیر ریشه و منطق ایجاد session را در Service trace کن تا علت پاسخ‌های خالی 200 مشخص شود.
3. از یک نامه آزمایشی، metadata درخواست واقعی مرورگر به loopback را ثبت کن؛ Cookie، token، متن نامه، امضا و تصویر نباید ذخیره یا منتشر شوند.
4. heartbeat واقعی Agent و رفتار آن هنگام توقف Service را بررسی کن.
5. تا زمان مشاهده درخواست واقعی و تطبیق پاسخ، سازگاری POST، dispatch XML و round-trip سند را تأییدشده اعلام نکن.


## Cross-project Winux Engine updates — relevance to EMWAT (2026-11-15)

The separate Winux development work has progressed beyond the initial runtime experiment. The latest working-tree context reports the following capabilities/design decisions; these are Winux capabilities, not proof that EMWAT itself has been integrated with them:

- A ServiceBackend contract with SystemdUserBackend, dependency-injected backend selection, and a systemd user-service default. A plugin entry-point mechanism (winux.service_backends) supports registered backends while recording plugin-load errors; it does not silently switch to an arbitrary backend.
- ServiceManager is kept separate from ProcessManager. Winux-managed services are Linux user services that supervise a foreground runner which launches a Windows application through Wine. This is not Windows Service Control Manager compatibility.
- winux doctor is intended to be read-only and validates Wine/prefix/runtime state. The latest reported PrefixManager hardening rejects symlinked path components beneath the user's home directory rather than following them during prefix operations.
- The current compatibility design supports x86 and x64 Windows applications through a 64-bit WoW64 prefix model where the installed Wine build supports it; separate pure 32-bit prefixes are not the default architecture.
- The latest Winux working-tree test baseline reported 216 passing tests. This is a Winux test result, not an EMWAT integration test.

### What EMWAT should reuse

1. Use the backend contract/injection pattern if EMWAT later needs multiple Linux service managers; retain a predictable systemd-user default rather than auto-selecting an unverified backend.
2. Keep process supervision separate from the HTTP bridge's application protocol and from document lifecycle logic.
3. Reuse the read-only diagnostics and symlink-safe path validation principles for EMWAT's runtime directories, temporary document files, and user-selected prefixes.
4. Keep x86/x64 architecture detection explicit in any Wine-based compatibility test harness. Do not assume a successful installer run proves that Agent, Service, Word automation, or printing works.
5. For the current Wine investigation only, Winux's service/process facilities may provide a controlled way to launch and observe the Windows binaries. The earlier experiment explicitly found that the running EmwatAgent.exe and EmwatService.exe processes were not yet tracked by Winux's ProcessManager or ServiceManager; that integration must be tested rather than assumed.

### Architecture boundary

These Winux improvements are development/test infrastructure and reusable engineering patterns. EMWAT-Linux's product target remains a native Linux bridge and document workflow using Linux-native components. Do not make Wine, Windows Service Control Manager emulation, a Windows kernel printer driver, or a Winux-specific runtime dependency of the final EMWAT architecture.

**Source freshness note:** the Winux local working-tree updates described above were reported in the separate Winux development session. The public Winux GitHub documentation snapshot may lag those local changes; verify the latest Winux source/tests before treating the 216-test baseline or newest backend/security behavior as a released, committed version.


## Public Winux repository cross-check — 2026-11-15

The latest public Winux repository was checked directly against its current source and documentation. This supersedes the earlier caution that managed-service work was only present in a separate local working tree:

- Public commit ef006c3 adds managed application services, including ServiceManager, SystemdUserBackend, the foreground service runner, and CLI lifecycle commands.
- Public commit 221def3 adds ProcessManager separately from ServiceManager. Do not use process tracking and long-running service supervision as interchangeable concepts.
- Public source includes a RuntimeManager with Wine as the default runtime and discovery of registered runtime plugins through the winux.runtimes entry-point group. Plugin load/registration errors are retained and logged; a plugin is not silently selected as the default.
- Public source includes VerificationManager profiles with file, process, port, and registry check types. Port checks are restricted to loopback/localhost. This can support a future Wine-harness verification profile for the EMWAT process and port 1984, but no such EMWAT profile has yet been executed.
- The architecture and handoff docs continue to define 64-bit WoW64 prefixes for x86/x64 Windows applications where the installed Wine build supports them.
- Winux-managed services remain Linux user services that supervise Windows applications through Wine; they are not native Windows SCM services.

### EMWAT integration decision

For the Windows compatibility research harness only, evaluate Winux ServiceManager for EmwatService.exe and, separately if needed, EmwatAgent.exe. Before creating either service, verify each process's expected foreground behavior, shutdown behavior, working directory, environment, and whether one depends on the other. The earlier runtime experiment found both processes running but not tracked by Winux managers; that gap is still not proof that service supervision is required.

Do not make this integration a prerequisite for the native EMWAT-Linux product. The final product remains a native Linux bridge and Writer workflow, with Linux-native process/service management chosen according to its own lifecycle requirements.

**Test-count boundary:** the previously reported 216 passing Winux tests came from the separate local working-tree report. It is not inferred from these source commits and is not an EMWAT integration test. Use the Winux repository's actual CI result for any public test-count claim.
