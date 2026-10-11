import { createContext, useContext } from "react";

export type Locale = "en" | "ar";

export const LocaleContext = createContext<Locale>("en");
export const useLocale = () => useContext(LocaleContext);

const arabic: Record<string, string> = {
  "My strips": "أجهزتي",
  "Consumption": "الاستهلاك",
  "Automation": "الأتمتة",
  "Rooms": "الغرف",
  "Add strip": "إضافة مشترك",
  "Settings": "الإعدادات",
  "Refresh": "تحديث",
  "Back to My strips": "الرجوع للأجهزة",
  "Primary": "التنقل الرئيسي",
  "Quick actions": "إجراءات سريعة",
  "Schedules": "الجداول",
  "Power automation": "أتمتة الطاقة",
  "Search strips and outlets": "ابحث عن مشترك أو مخرج",
  "Cancel": "إلغاء",
  "Close": "إغلاق",
  "Outlet": "مخرج",
  "ON": "يعمل",
  "OFF": "متوقف",
  "ONLINE": "متصل",
  "OFFLINE": "غير متصل",
  "DISABLED": "معطّل",
  "Turn all on": "تشغيل الكل",
  "Turn all off": "إيقاف الكل",
  "Local strip": "مشترك محلي",
  "Total power right now": "الاستهلاك اللحظي",
  "Connected": "متصل",
  "Active outlets": "مخارج تعمل",
  "Active schedules": "جداول نشطة",
  "strips online": "مشتركات متصلة",
  "outlets on": "مخارج تعمل",
  "plans active": "جداول نشطة",
  "Your strips": "المشتركات",
  "LIVE DEVICES": "الأجهزة المباشرة",
  "Search results": "نتائج البحث",
  "No matching strips": "لا توجد نتائج مطابقة",
  "No strips yet": "لم تتم إضافة أجهزة",
  "Try a strip name, room, MAC address, or mapped device name.": "جرّب اسم المشترك أو الغرفة أو عنوان MAC أو اسم الجهاز المرتبط.",
  "Add your first MTTL-W01 strip and it will appear here.": "أضف أول مشترك MTTL-W01 وسيظهر هنا.",
  "Monitor and control your space": "راقب وتحكم في أجهزتك من مكان واحد",
  "All your power, one place.": "كل طاقتك تحت السيطرة.",
  "Overview": "نظرة عامة",
  "Your smart power control center": "مركز التحكم الذكي بالطاقة",
  "POWER OVERVIEW": "ملخص الطاقة",
  "Switch outlets, track usage, and automate every room.": "تحكم بالمخارج وتابع الاستهلاك وأنشئ الأتمتة لكل غرفة.",
  "Live monitoring": "مراقبة مباشرة",
  "Devices": "الأجهزة",
  "Manage your connected power strips": "إدارة المشتركات المتصلة",
  "Open settings": "فتح الإعدادات",
  "Settings for": "إعدادات",
  "Change language": "تغيير اللغة",
  "English": "English",
  "العربية": "العربية",
  "Power controls": "التحكم بالطاقة",
  "Voltra Local": "فولترا المحلي",
  "Local mini server": "سيرفر محلي مصغّر",
  "Turn all outlets on?": "تشغيل جميع المخارج؟",
  "Turn all outlets off?": "إيقاف جميع المخارج؟",
  "Turn all outlets on": "تشغيل جميع المخارج",
  "Turn all outlets off": "إيقاف جميع المخارج",
  "All outlets are on.": "تم تشغيل كل المخارج.",
  "All outlets are off.": "تم إيقاف كل المخارج.",
  "Some outlets could not be updated. Please check device status.": "تعذر تحديث بعض المخارج؛ راجع حالة الجهاز.",
  "Strip settings saved.": "تم حفظ إعدادات المشترك.",
  "Strip removed.": "تم حذف المشترك.",
  "Remove this strip?": "حذف المشترك؟",
  "Remove strip": "حذف المشترك",
  "Strip name": "اسم المشترك",
  "Room": "الغرفة",
  "Favorite": "مفضّل",
  "Control enabled": "التحكم مفعّل",
  "Save changes": "حفظ التغييرات",
  "Choose an outlet first.": "اختر مخرجًا أولًا.",
  "Energy": "الطاقة",
  "SYSTEM": "النظام",
  "ONBOARDING": "إضافة الأجهزة",
  "Waiting for a new strip": "في انتظار مشترك جديد",
  "New strips": "المشتركات الجديدة",
  "New MTTL-W01": "مشترك MTTL-W01 جديد",
  "WI-FI SETUP": "إعداد واي فاي",
  "Provision a new strip": "تهيئة مشترك جديد",
  "Send network settings": "إرسال إعدادات الشبكة",
  "Current load": "الحمل الحالي",
  "Online strips": "المشتركات المتصلة",
  "Server version": "إصدار السيرفر",
  "Configuration safety": "حماية الإعدادات",
  "Export backup": "تصدير نسخة احتياطية",
  "Restore backup": "استعادة نسخة احتياطية",
  "Diagnostics": "التشخيص",
  "Cost settings": "إعدادات التكلفة",
  "Save settings": "حفظ الإعدادات",
  "Legacy console": "الواجهة القديمة",
  "Open": "فتح",
};

export function t(locale: Locale, text: string): string {
  return locale === "ar" ? arabic[text] || text : text;
}

export function initialLocale(): Locale {
  try {
    return window.localStorage.getItem("voltra.ui.locale") === "ar" ? "ar" : "en";
  } catch {
    return "en";
  }
}

export function persistLocale(value: Locale): void {
  try {
    window.localStorage.setItem("voltra.ui.locale", value);
  } catch {
    // Private browsing may restrict local storage; switching still works in memory.
  }
}
