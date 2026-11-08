# Voltra v0.23 — Firmware-native control (MTTL-W01 Standalone)

## إضافة المشترك

1. وصل المشترك بشبكة Wi-Fi المحلية وثبت له DHCP reservation إن أمكن.
2. افتح Voltra → Add strip → Connect by device IP، ثم اكتب **IP المشترك نفسه** وليس IP CasaOS.
3. Voltra يتحقق من MAC والفيرموير 2.1.x، ثم يعرضه Pending للموافقة.
4. بعد الموافقة، اضغط Open native controls, schedules & settings.

## الوظائف الجديدة

- Power strip: الأزرار السريعة عبر firmware /api/control مع ON/OFF وALL، وأسماء المخارج وقفل الأزرار الفيزيائية واللغة.
- Wi-Fi setup: Scan للشبكات وتغيير الاتصال (قد يحتاج إعادة Pairing لو تغير IP).
- HA · MQTT: عنوان Broker والمنفذ واسم المستخدم والباسورد وTopic Prefix.
- Protection: حدود الحرارة والتيار والقدرة وحالة الحماية.
- Scheduler: ثمانية مواعيد يومية أو أسبوعية أو شهرية أو آخر يوم في الشهر.
- Timer: 0–1440 دقيقة لكل مخرج، والحفظ مباشرة داخل Flash المشترك.
- Firmware: عرض النسخة والـ Build ID ورفع FWR عند توفر خيار OTA في الفيرموير.
- Logs: سجل أحداث Voltra والتشخيصات؛ سجل الواجهة الأصلية محفوظ في المتصفح وليس له API مستقلة.

## الحفظ الحقيقي على المشترك

يستخدم Voltra صيغة firmware binary v7، وفيها 50 بايت للجداول (2 timezone + 8 rules × 6 bytes).
يمنع تعارض Auto OFF Timer مع Schedule على المخرج نفسه.
عند الحفظ يرسل POST مرة واحدة، ثم يقرأ إعدادات الجهاز ويتأكد من استمرارها في Flash.
لا يكرر POST تلقائيًا إذا الرد ضاع. كلمة مرور Wi-Fi تُحفظ ولا يعاد إرسالها.
الجداول محفوظة في الجهاز حتى لو Voltra/Mosquitto توقفا، لكن قواعد التقويم تتطلب ساعة NTP صحيحة؛ اضبط توقيت مصر صيفًا وشتاءً يدويًا.

## الأمان

- اقتران IP يقتصر على عناوين RFC1918 المحلية (لا URL ولا DNS ولا localhost).
- يُتحقق من MAC الجهاز الفعلي قبل كل كتابة.
- لا تُتاح وظائف التعديل إلا بعد Adopt ووجود صلاحية Voltra.
- واجهة firmware HTTP الأصلية لا توفر تسجيل دخول خاص بها؛ اعزل الأجهزة على LAN موثوقة.
- رفع FWR خطير ومتاح فقط عند OTA readiness وبموافقة صريحة. لا تفصل الكهرباء ولا تعيد الرفع تلقائيًا.
- لا تفتح port 80 أو MQTT 1883 من الإنترنت.

## ترقية CasaOS

بعد دمج PR في main:

    cd ~/voltra-local-mini-server
    git pull --ff-only origin main
    sudo bash casaos/install.sh
    sudo bash casaos/check-mqtt.sh

حافظ على Backup تلقائيًا؛ لا تحذف Voltra data ولا تستخدم docker compose down -v.

## اختبار على الهاردوير

جرّب مشتركًا واحدًا أولًا، على مخرج بحمل آمن: ON/OFF، ثم حفظ موعد محلي، ثم Refresh، ثم تعطيل Voltra مؤقتًا ومراقبة تنفيذ الموعد الداخلي.
الاختبارات الآلية في GitHub لا تحل محل اختبار الريلاي فعليًا أو صحة ساعة NTP.
