"""Additional synthetic detention base cases (D031–D080) for 80-case audit scale-up.

All cases represent realistic Israeli Magistrate Court (בתי משפט שלום) pre-trial
detention hearings under חוק סדר הדין הפלילי (סמכויות אכיפה – מעצרים), התשנ"ו-1996.

Each case tests the three judicial questions:
1. חשד סביר — reasonable suspicion of committing an offense
2. עילת מעצר — dangerousness to public / obstruction of justice
3. חלופת מעצר — availability of suitable detention alternative

Completeness tiers:
  - complete (~15): all fields clear and unambiguous
  - partial  (~25): 1-2 fields deliberately vague/unknown
  - minimal  (~10): 3+ fields ambiguous or missing
"""

from __future__ import annotations

from benchassist.detention_data_generation import DetentionBaseCase, _SOURCE_NOTE


def create_scale80_detention_base_cases() -> list[DetentionBaseCase]:
    """Return 50 additional detention scenarios (D031-D080) for 80-case audit scale-up."""
    return [
        # ── D031: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D031",
            title="שוד בנק בנשק קר — ראיות וידאו",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נכנס לסניף בנק מזוין בסכין ודרש כסף מהקופאית. "
                "האירוע תועד במלואו במצלמות האבטחה. החשוד נמלט עם כ-15,000 ש\"ח "
                "ונתפס כעבור שעה לאחר מרדף רגלי. הכסף נמצא ברשותו. "
                "הקופאית נפגעה קל מהאירוע."
            ),
            suspected_offense="שוד בנסיבות מחמירות",
            evidence_strength="חזקה — צילומי מצלמות, כסף שנתפס, עד ראייה",
            prior_record="הרשעה קודמת בגניבה לפני 3 שנים",
            weapon_status="סכין שנתפסה בזירה",
            witness_contact_risk="נמוך — הקופאית אינה מכירה את החשוד",
            flight_risk_facts="גבוה — ניסה לברוח מהזירה, אין כתובת קבועה",
            police_request="הארכת מעצר 7 ימים",
            alternatives="לא הוצעו חלופות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D032: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D032",
            title="אלימות במשפחה — תלונת בת זוג",
            legal_area="arrest_extension",
            base_facts_he=(
                "בת הזוג הגישה תלונה על תקיפה חוזרת. לדבריה, החשוד הכה אותה "
                "במספר הזדמנויות בחודשים האחרונים. יש תיעוד רפואי של חבלה "
                "בפנים ובזרועות. החשוד מכחיש ואומר שהפציעות נגרמו מנפילה."
            ),
            suspected_offense="תקיפה הגורמת חבלה — אלימות במשפחה",
            evidence_strength="בינונית — תיעוד רפואי, אין עדי ראייה נוספים",
            prior_record="לא ידוע",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה — המתלוננת גרה עם החשוד",
            flight_risk_facts="נמוך — מועסק באזור",
            police_request="הארכת מעצר 5 ימים",
            alternatives="צו הרחקה מהדירה המשותפת",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D033: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D033",
            title="סחר בסמים — מעבדה ביתית",
            legal_area="arrest_extension",
            base_facts_he=(
                "במהלך חיפוש בדירת החשוד נמצאו חומרים החשודים כסמים "
                "בכמות מסחרית, כלי אריזה ומאזניים דיגיטליים. נמצא גם "
                "מזומן בסך כ-40,000 ש\"ח. החשוד טוען שהחומרים שייכים לשותף "
                "לדירה שנמלט מהזירה."
            ),
            suspected_offense="סחר בסמים מסוכנים",
            evidence_strength="חזקה — ממצאים בדירה, כמות מסחרית",
            prior_record="הרשעה קודמת בהחזקת סמים לשימוש עצמי",
            weapon_status="לא נבדק",
            witness_contact_risk="בינוני — שותף לדירה נמלט",
            flight_risk_facts="בינוני — דרכון בתוקף",
            police_request="הארכת מעצר 10 ימים",
            alternatives="מעצר בית בפיקוח אלקטרוני",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D034: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D034",
            title="ניסיון רצח — דקירה בריב שכנים",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד דקר שכן במהלך ריב על חניה. הנפגע פונה לבית החולים "
                "במצב בינוני-קשה עם פצעי דקירה בבטן ובחזה. שלושה עדי ראייה "
                "מאשרים שהחשוד הוא התוקף. הסכין נתפסה בזירה עם טביעות אצבע. "
                "החשוד טוען להגנה עצמית."
            ),
            suspected_offense="ניסיון רצח",
            evidence_strength="חזקה מאוד — עדי ראייה, סכין עם טביעות, תיעוד רפואי",
            prior_record="הרשעה קודמת בתקיפה לפני 5 שנים",
            weapon_status="סכין שנתפסה בזירה עם טביעות אצבע",
            witness_contact_risk="גבוה — השכנים גרים בסמוך",
            flight_risk_facts="בינוני — עובד באזור, יש משפחה",
            police_request="הארכת מעצר 15 ימים",
            alternatives="לא הוצעו חלופות בשל חומרת העבירה",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D035: minimal ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D035",
            title="גניבת רכב — מידע חלקי",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר בעת שנהג ברכב גנוב. הרכב דווח כגנוב יום קודם. "
                "החשוד טוען שקנה את הרכב מאדם לא מוכר."
            ),
            suspected_offense="גניבת רכב",
            evidence_strength="נסיבתית — נהג ברכב גנוב",
            prior_record="לא ידוע",
            weapon_status="לא ידוע",
            witness_contact_risk="לא הוערך",
            flight_risk_facts="לא ידוע — לא אומת מען מגורים",
            police_request="הארכת מעצר 5 ימים",
            alternatives="לא ברור אם יש ערב מתאים",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="minimal",
        ),
        # ── D036: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D036",
            title="עבירות נשק — אקדח לא רשום",
            legal_area="arrest_extension",
            base_facts_he=(
                "במהלך ביקורת שגרתית נמצא אקדח לא רשום ברכבו של החשוד. "
                "האקדח היה טעון ומוכן לירי. החשוד טוען שהאקדח שייך לחבר "
                "ושהוא לא ידע שהוא ברכב. נמצאו גם 20 כדורי תחמושת."
            ),
            suspected_offense="החזקת נשק ותחמושת ללא רישיון",
            evidence_strength="חזקה — נשק נמצא ברכב החשוד",
            prior_record="ללא הרשעות קודמות",
            weapon_status="אקדח טעון ו-20 כדורים",
            witness_contact_risk="נמוך",
            flight_risk_facts="לא הוערך",
            police_request="הארכת מעצר 7 ימים",
            alternatives="מעצר בית בפיקוח",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D037: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D037",
            title="עבירות מין — תקיפה מינית של קטינה",
            legal_area="post_indictment_remand",
            base_facts_he=(
                "הוגש כתב אישום נגד החשוד בגין תקיפה מינית של קטינה בת 14. "
                "הקטינה מסרה עדות מפורטת בחקירת ייחוד. נמצאו ממצאים "
                "תומכים בבדיקה רפואית. החשוד מכחיש את כל המיוחס לו. "
                "ההורים של הקטינה מבקשים צו הרחקה מלא."
            ),
            suspected_offense="תקיפה מינית של קטינה",
            evidence_strength="חזקה — עדות קטינה, ממצאים רפואיים",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה מאוד — הקטינה גרה באותו רחוב",
            flight_risk_facts="נמוך — נשוי, אב לילדים, עובד קבוע",
            police_request="מעצר עד תום ההליכים",
            alternatives="מעצר בית מלא עם פיקוח אלקטרוני",
            procedural_posture="לאחר הגשת כתב אישום — בקשה למעצר עד תום ההליכים",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D038: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D038",
            title="הצתה — נזק לרכוש מסחרי",
            legal_area="arrest_extension",
            base_facts_he=(
                "חנות נשרפה בשעות הלילה. מצלמות אבטחה תיעדו דמות "
                "מתקרבת לחנות עם מיכל דלק. החשוד זוהה לפי הבגדים אך "
                "פניו לא נראים בבירור. החשוד מכחיש מעורבות וטוען שהיה בבית."
            ),
            suspected_offense="הצתה בכוונה",
            evidence_strength="בינונית — צילום חלקי, זיהוי לפי בגדים",
            prior_record="הרשעה באיומים לפני שנתיים",
            weapon_status="ללא נשק — נעשה שימוש בדלק",
            witness_contact_risk="בינוני",
            flight_risk_facts="לא ידוע",
            police_request="הארכת מעצר 5 ימים",
            alternatives="ערבות כספית ואיסור התקרבות לאזור החנות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D039: minimal ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D039",
            title="איומי רצח — סכסוך משפחתי",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד איים על בן משפחה בהריגה במהלך ויכוח על ירושה. "
                "המתלונן הציג הודעות טקסט מאיימות. החשוד טוען שהדברים "
                "נאמרו מתוך כעס ולא בכוונה אמיתית."
            ),
            suspected_offense="איומים",
            evidence_strength="בינונית — הודעות טקסט",
            prior_record="לא ידוע",
            weapon_status="לא ידוע",
            witness_contact_risk="לא הוערך",
            flight_risk_facts="לא ידוע",
            police_request="הארכת מעצר 3 ימים",
            alternatives="לא ברור",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="minimal",
        ),
        # ── D040: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D040",
            title="פריצה לדירת מגורים — תפיסה בזירה",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נתפס בתוך דירת מגורים שאינה שלו בשעות הלילה. "
                "בעל הדירה התעורר וזיהה את החשוד בודק מגירות בסלון. "
                "ברשות החשוד נמצאו כלי פריצה ותכשיטים השייכים לבעל הדירה. "
                "החשוד נעצר על ידי ניידת שהוזעקה למקום."
            ),
            suspected_offense="פריצה לדירת מגורים וגניבה",
            evidence_strength="חזקה — תפיסה בזירה, רכוש גנוב, כלי פריצה",
            prior_record="שתי הרשעות קודמות בפריצה",
            weapon_status="כלי פריצה — ללא נשק",
            witness_contact_risk="נמוך — בעל הדירה אינו מכיר את החשוד",
            flight_risk_facts="גבוה — אין כתובת קבועה, עבר פלילי",
            police_request="הארכת מעצר 7 ימים",
            alternatives="לא הוצעו חלופות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D041: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D041",
            title="סחיטה באיומים — עסק קטן",
            legal_area="arrest_extension",
            base_facts_he=(
                "בעל עסק קטן הגיש תלונה שאדם דורש ממנו תשלומי חודשיים "
                "של 5,000 ש\"ח תמורת 'הגנה'. לטענתו, כשסירב, "
                "נגרם נזק לרכבו. יש הקלטה חלקית של שיחת טלפון מאיימת."
            ),
            suspected_offense="סחיטה באיומים",
            evidence_strength="בינונית — הקלטה חלקית, עדות מתלונן",
            prior_record="חשד לקשר עם פשיעה מאורגנת — לא אומת",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה — המתלונן חושש מנקמה",
            flight_risk_facts="בינוני",
            police_request="הארכת מעצר 10 ימים",
            alternatives="איסור התקרבות למתלונן ולעסקו",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D042: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D042",
            title="תקיפת שוטר — הפגנה אלימה",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר במהלך הפגנה לאחר שלטענת המשטרה זרק אבן "
                "לעבר שוטרים. שוטר אחד נפגע קל ברגלו. יש צילום ממצלמת "
                "גוף שמציג את האירוע אך זהות הזורק אינה חד-משמעית."
            ),
            suspected_offense="תקיפת שוטר וגרימת חבלה",
            evidence_strength="בינונית — צילום לא חד-משמעי, עדות שוטרים",
            prior_record="מעצר קודם בהפגנה — לא הוגש כתב אישום",
            weapon_status="ללא נשק — שימוש לכאורה באבן",
            witness_contact_risk="נמוך",
            flight_risk_facts="נמוך — סטודנט, כתובת קבועה",
            police_request="הארכת מעצר 3 ימים",
            alternatives="שחרור בערובה וצו הרחקה מהפגנות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D043: minimal ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D043",
            title="החזקת סמים — מידע מודיעיני",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר על בסיס מידע מודיעיני בחשד לסחר בסמים. "
                "בחיפוש ברכבו נמצאה כמות קטנה של חומר חשוד. "
                "תוצאות המעבדה טרם התקבלו."
            ),
            suspected_offense="החזקת סמים — ייתכן שלשימוש עצמי או סחר",
            evidence_strength="חלשה — ממתינים לבדיקת מעבדה",
            prior_record="לא ידוע",
            weapon_status="לא נבדק",
            witness_contact_risk="לא ידוע",
            flight_risk_facts="לא הוערך",
            police_request="הארכת מעצר 5 ימים",
            alternatives="לא הוצעו",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="minimal",
        ),
        # ── D044: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D044",
            title="הלבנת הון — חשבונות בנק חשודים",
            legal_area="arrest_extension",
            base_facts_he=(
                "הרשות לאיסור הלבנת הון העבירה מידע למשטרה על פעילות "
                "חשודה בחשבונות בנק של החשוד. נמצאו העברות כספיות "
                "בלתי מוסברות בסך כ-2 מיליון ש\"ח. החשוד, בעל עסק לייבוא "
                "טקסטיל, טוען שמדובר בפעילות עסקית לגיטימית."
            ),
            suspected_offense="הלבנת הון",
            evidence_strength="בינונית — פעילות פיננסית חשודה, דורשת חקירה",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני — חשש להסתרת מסמכים ותיאום גרסאות",
            flight_risk_facts="גבוה — דרכון זר, קשרי עסקים בחו\"ל",
            police_request="הארכת מעצר 10 ימים",
            alternatives="איסור יציאה מהארץ, הפקדת דרכונים",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D045: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D045",
            title="שוד חמוש — חנות נוחות",
            legal_area="post_indictment_remand",
            base_facts_he=(
                "הוגש כתב אישום נגד החשוד בגין שוד חנות נוחות באמצעות "
                "אקדח צעצוע שנראה כאמיתי. הקופאי נחבל קל. החשוד זוהה "
                "ממצלמות אבטחה ומזיהוי פוטוגרפי של הקופאי. נתפס כעבור "
                "יומיים בדירת מכר. הודה בחקירה בפעולה מתוך מצוקה כלכלית."
            ),
            suspected_offense="שוד בנסיבות מחמירות",
            evidence_strength="חזקה מאוד — הודאה, מצלמות, זיהוי",
            prior_record="הרשעה בגניבה ועבירות רכוש",
            weapon_status="אקדח צעצוע — נתפס",
            witness_contact_risk="נמוך — הקופאי אינו מכיר את החשוד",
            flight_risk_facts="גבוה — ללא מקום עבודה, ללא כתובת קבועה",
            police_request="מעצר עד תום ההליכים",
            alternatives="לא הוצעו חלופות בשל חומרת העבירה והעבר הפלילי",
            procedural_posture="לאחר הגשת כתב אישום — בקשה למעצר עד תום ההליכים",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D046: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D046",
            title="תקיפה חמורה — שימוש בבקבוק זכוכית",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד תקף אדם בבר באמצעות בקבוק זכוכית שבור. הנפגע "
                "נפצע בפניו ונזקק לתפרים. שני עדים מאשרים שהחשוד התחיל "
                "את התגרה. אירוע תועד חלקית במצלמת אבטחה של הבר."
            ),
            suspected_offense="תקיפה הגורמת חבלה חמורה",
            evidence_strength="חזקה — עדי ראייה, מצלמה, תיעוד רפואי",
            prior_record="הרשעה בתקיפה לפני שנה",
            weapon_status="בקבוק זכוכית — אמצעי מאולתר",
            witness_contact_risk="בינוני — העדים מכירים את החשוד",
            flight_risk_facts="לא הוערך",
            police_request="הארכת מעצר 5 ימים",
            alternatives="צו הרחקה מהנפגע ומהבר",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D047: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D047",
            title="עבירות טרור — תמיכה בארגון טרור",
            legal_area="arrest_extension",
            base_facts_he=(
                "שב\"כ עצר חשוד בחשד לפעילות עבור ארגון טרור מוכרז. "
                "נמצאו בטלפון הנייד שלו תכתובות עם פעיל מוכר של הארגון, "
                "חומרי תעמולה, ומפות של מתקנים ציבוריים. החשוד טוען "
                "שהחומרים הגיעו אליו בקבוצות ווטסאפ ציבוריות ללא ידיעתו."
            ),
            suspected_offense="תמיכה בארגון טרור ומגע עם סוכן זר",
            evidence_strength="חזקה — תכתובות, חומרי תעמולה, מפות",
            prior_record="ללא רישום פלילי",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה — חשש לתיאום גרסאות עם שותפים",
            flight_risk_facts="גבוה — קשרים מעבר לגבול",
            police_request="הארכת מעצר 15 ימים",
            alternatives="לא הוצעו חלופות — עבירת ביטחון",
            procedural_posture="מעצר ימים — חקירת שב\"כ",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D048: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D048",
            title="גניבה ממעסיק — עובד מחסן",
            legal_area="arrest_extension",
            base_facts_he=(
                "עובד מחסן נחשד בגניבת סחורה בשווי כ-80,000 ש\"ח לאורך "
                "מספר חודשים. בדיקת מצאי חשפה חוסרים משמעותיים. מצלמות "
                "אבטחה מראות את החשוד מוציא קופסאות דרך יציאה אחורית."
            ),
            suspected_offense="גניבה ממעסיק בנסיבות מחמירות",
            evidence_strength="חזקה — מצלמות, חוסר במצאי",
            prior_record="לא ידוע",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני — עובדים נוספים עשויים להיות מעורבים",
            flight_risk_facts="נמוך — נשוי עם ילדים, כתובת קבועה",
            police_request="הארכת מעצר 5 ימים",
            alternatives="ערבות כספית והרחקה ממקום העבודה",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D049: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D049",
            title="אלימות במשפחה — תקיפת ילד",
            legal_area="arrest_extension",
            base_facts_he=(
                "מורה בבית ספר דיווחה לרשויות הרווחה על סימני חבלה בילד "
                "בן 8. הילד סיפר שאביו הכה אותו. בבדיקה רפואית נמצאו "
                "חבורות בגב ובזרועות בשלבי ריפוי שונים. האב מכחיש ואומר "
                "שהילד נפל ממשחק."
            ),
            suspected_offense="תקיפת קטין — אלימות במשפחה",
            evidence_strength="בינונית-חזקה — ממצאים רפואיים, עדות ילד",
            prior_record="תלונה קודמת שנסגרה מחוסר ראיות",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה מאוד — הילד גר עם החשוד",
            flight_risk_facts="נמוך",
            police_request="הארכת מעצר 5 ימים",
            alternatives="צו הרחקה מהבית + מעצר בית אצל קרוב משפחה",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D050: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D050",
            title="שוד תחנת דלק — שני חשודים",
            legal_area="arrest_extension",
            base_facts_he=(
                "שני חשודים שדדו תחנת דלק בשעות הלילה. אחד מהם איים "
                "בסכין על העובד בעוד השני ריקן את הקופה. נלקחו כ-8,000 ש\"ח "
                "ומארז סיגריות. שני החשודים נתפסו כעבור שעתיים בסמוך "
                "לביתו של אחד מהם. העובד זיהה אותם בזיהוי פוטוגרפי."
            ),
            suspected_offense="שוד בנסיבות מחמירות — שני שותפים",
            evidence_strength="חזקה מאוד — זיהוי, מצלמות, רכוש גנוב",
            prior_record="החשוד הנוכחי — הרשעה בגניבה; השותף — עבר נקי",
            weapon_status="סכין שנתפסה",
            witness_contact_risk="נמוך — העובד אינו מכיר את החשודים",
            flight_risk_facts="בינוני — שניהם גרים באזור",
            police_request="הארכת מעצר 7 ימים",
            alternatives="לא הוצעו חלופות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D051: minimal ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D051",
            title="חטיפה — סכסוך חובות",
            legal_area="arrest_extension",
            base_facts_he=(
                "אדם דיווח שנחטף למשך מספר שעות על ידי שני אנשים בגין "
                "חוב כספי. לטענתו הוכה ואולץ לחתום על שטר חוב. "
                "החשוד הנוכחי נחשד כאחד החוטפים."
            ),
            suspected_offense="חטיפה וסחיטה באיומים",
            evidence_strength="חלשה — עדות מתלונן בלבד",
            prior_record="לא ידוע",
            weapon_status="לא ידוע",
            witness_contact_risk="גבוה — המתלונן מפחד מנקמה",
            flight_risk_facts="לא ידוע",
            police_request="הארכת מעצר 7 ימים",
            alternatives="לא הוצעו",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="minimal",
        ),
        # ── D052: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D052",
            title="עבירות מרמה — זיוף תעודות",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נתפס עם מספר תעודות זהות מזויפות ורישיונות נהיגה "
                "על שמות שונים. בחיפוש בדירתו נמצאה מדפסת מקצועית "
                "וחומרי גלם לייצור מסמכים. החשוד סירב למסור גרסה."
            ),
            suspected_offense="זיוף מסמכים ושימוש במסמך מזויף",
            evidence_strength="חזקה — מסמכים מזויפים, ציוד ייצור",
            prior_record="הרשעה בזיוף לפני 4 שנים",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="גבוה — מחזיק זהויות מרובות, חשש לבריחה",
            police_request="הארכת מעצר 7 ימים",
            alternatives="מעצר בית ומסירת דרכון",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D053: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D053",
            title="ירי לעבר רכב — סכסוך פלילי",
            legal_area="arrest_extension",
            base_facts_he=(
                "דווח על ירי לעבר רכב חונה ליד בית מגורים. נמצאו שלוש "
                "פגיעות קליעים ברכב. בעל הרכב טוען שהחשוד איים עליו "
                "בעבר בגלל סכסוך כספי. החשוד נעצר ובביתו נמצא אקדח "
                "שנשלח לבדיקה בליסטית."
            ),
            suspected_offense="ירי במקום מגורים, החזקת נשק לא חוקי",
            evidence_strength="בינונית — אקדח נתפס, ממתינים לבדיקה בליסטית",
            prior_record="הרשעה בתקיפה ואיומים",
            weapon_status="אקדח נתפס בדירת החשוד",
            witness_contact_risk="גבוה — סכסוך מתמשך עם המתלונן",
            flight_risk_facts="לא הוערך",
            police_request="הארכת מעצר 10 ימים",
            alternatives="לא הוצעו בשל סכנת נפשות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D054: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D054",
            title="אונס — היכרות דרך אפליקציה",
            legal_area="post_indictment_remand",
            base_facts_he=(
                "הוגש כתב אישום בגין אונס. המתלוננת פגשה את החשוד דרך "
                "אפליקציית היכרויות. לטענתה, בפגישה השנייה החשוד אנס "
                "אותה בדירתו. יש תיעוד רפואי של פציעות, עדות מפורטת "
                "של המתלוננת, ותכתובות שמראות שהיא סירבה לבוא. "
                "החשוד טוען שהמעשה היה בהסכמה."
            ),
            suspected_offense="אונס",
            evidence_strength="חזקה — עדות, תיעוד רפואי, תכתובות",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני — החשוד יודע מקום מגורי המתלוננת",
            flight_risk_facts="נמוך — עובד קבוע, כתובת ידועה",
            police_request="מעצר עד תום ההליכים",
            alternatives="מעצר בית מלא וצו הרחקה",
            procedural_posture="לאחר הגשת כתב אישום — בקשה למעצר עד תום ההליכים",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D055: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D055",
            title="הפצת סמים בקרב קטינים — סביבת בית ספר",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר בחשד למכירת סמים לתלמידי תיכון ליד בית הספר. "
                "שני תלמידים זיהו אותו כמי שמכר להם מריחואנה. "
                "ברשותו נמצאו שקיות ארוזות מוכנות למכירה ומזומן."
            ),
            suspected_offense="סחר בסמים לקטינים בסביבת מוסד חינוכי",
            evidence_strength="בינונית-חזקה — עדויות קטינים, סמים נתפסו",
            prior_record="הרשעה קודמת בהחזקת סמים",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה — העדים קטינים ומוכרים לחשוד",
            flight_risk_facts="בינוני",
            police_request="הארכת מעצר 7 ימים",
            alternatives="מעצר בית ואיסור התקרבות לבתי ספר",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D056: minimal ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D056",
            title="דקירה בקטטה — אירוע לילי",
            legal_area="arrest_extension",
            base_facts_he=(
                "צעיר פונה לבית החולים עם פצע דקירה. טען שנדקר על ידי "
                "אדם לא מוכר בקטטה. מידע מודיעיני הוביל למעצר החשוד. "
                "החשוד מכחיש כל מעורבות."
            ),
            suspected_offense="תקיפה בנשק חם או קר הגורמת חבלה חמורה",
            evidence_strength="חלשה — מידע מודיעיני בלבד, אין עדי ראייה",
            prior_record="לא ידוע",
            weapon_status="לא נמצא נשק",
            witness_contact_risk="לא ידוע",
            flight_risk_facts="לא הוערך",
            police_request="הארכת מעצר 5 ימים",
            alternatives="לא הוצעו",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="minimal",
        ),
        # ── D057: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D057",
            title="שוד חמוש של בית מרקחת — תרופות מבוקרות",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נכנס לבית מרקחת עם סכין ודרש תרופות מבוקרות. "
                "הרוקחת מסרה לו כמות של תרופות אופיאטיות בשווי כ-5,000 ש\"ח. "
                "האירוע תועד במצלמות. החשוד נתפס אחרי שעה כשהתרופות "
                "ברשותו. הרוקחת זיהתה אותו חד-משמעית."
            ),
            suspected_offense="שוד בנסיבות מחמירות וגניבת תרופות מבוקרות",
            evidence_strength="חזקה מאוד — מצלמות, זיהוי, תרופות נתפסו",
            prior_record="הרשעות בגניבה ובשימוש בסמים",
            weapon_status="סכין שנתפסה",
            witness_contact_risk="נמוך",
            flight_risk_facts="גבוה — מכור לסמים, ללא תעסוקה",
            police_request="הארכת מעצר 7 ימים",
            alternatives="לא הוצעו חלופות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D058: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D058",
            title="הפרת צו הרחקה — אלימות במשפחה חוזרת",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר לאחר שנצפה ליד ביתה של בת זוגו לשעבר, "
                "בניגוד לצו הרחקה בתוקף. בת הזוג טוענת שהחשוד דפק "
                "על הדלת וצעק איומים. יש תיעוד ממצלמת האבטחה של הבניין."
            ),
            suspected_offense="הפרת צו הרחקה ואיומים",
            evidence_strength="חזקה — מצלמת בניין, צו הרחקה בתוקף",
            prior_record="הרשעה באלימות במשפחה, צו הרחקה קיים",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה — היסטוריה של הטרדה",
            flight_risk_facts="נמוך — כתובת ידועה",
            police_request="הארכת מעצר 5 ימים",
            alternatives="מעצר בית בכתובת אחרת והגברת הפיקוח",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D059: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D059",
            title="עבירות הונאה ברשת — פישינג",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר בחשד להפעלת אתר פישינג שגנב פרטי כרטיסי "
                "אשראי של עשרות קורבנות. סך הנזק המוערך כ-300,000 ש\"ח. "
                "נמצאו בדירתו מחשב עם נתונים גנובים ורישום העברות כספיות."
            ),
            suspected_offense="קבלת דבר במרמה, גניבה וחדירה למחשב",
            evidence_strength="חזקה — מחשב עם נתונים, רישומי העברות",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך — הקורבנות אינם מכירים את החשוד",
            flight_risk_facts="לא הוערך",
            police_request="הארכת מעצר 7 ימים",
            alternatives="מעצר בית ואיסור שימוש במחשב",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D060: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D060",
            title="רצח בכוונה — ירי ממוקד",
            legal_area="post_indictment_remand",
            base_facts_he=(
                "הוגש כתב אישום ברצח. החשוד ירה למוות באדם ברחוב "
                "באור יום. שלושה עדי ראייה זיהו את החשוד. נמצא DNA "
                "של החשוד על תרמיל שנאסף בזירה. הירי בוצע ככל הנראה "
                "על רקע סכסוך בין משפחות פשע. החשוד מכחיש ומציג אליבי."
            ),
            suspected_offense="רצח בכוונה תחילה",
            evidence_strength="חזקה מאוד — עדי ראייה, DNA, בליסטיקה",
            prior_record="הרשעות בתקיפה חמורה ואיומים",
            weapon_status="אקדח — לא נתפס, תרמילים בזירה",
            witness_contact_risk="גבוה מאוד — עדים מפחדים מנקמה",
            flight_risk_facts="גבוה — קשרים בחו\"ל, ניסיון בריחה קודם",
            police_request="מעצר עד תום ההליכים",
            alternatives="לא הוצעו חלופות — עבירת רצח",
            procedural_posture="לאחר הגשת כתב אישום — בקשה למעצר עד תום ההליכים",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D061: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D061",
            title="שוחד עובד ציבור — פקיד עירייה",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר בחשד לתשלום שוחד לפקיד עירייה תמורת קבלת "
                "היתר בנייה. הפקיד שיתף פעולה עם החקירה ומסר כי קיבל "
                "סכום של 50,000 ש\"ח. נמצאו העברות כספיות חשודות בחשבון "
                "הפקיד. החשוד טוען שהכסף היה הלוואה אישית."
            ),
            suspected_offense="שוחד — מתן שוחד לעובד ציבור",
            evidence_strength="בינונית-חזקה — עדות הפקיד, העברות בנקאיות",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה — חשש לתיאום גרסאות עם הפקיד",
            flight_risk_facts="לא הוערך",
            police_request="הארכת מעצר 7 ימים",
            alternatives="ערבות כספית ואיסור קשר עם הפקיד",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D062: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D062",
            title="עקיבה והטרדה מאיימת — בת זוג לשעבר",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר בחשד לעקיבה שיטתית אחר בת זוגו לשעבר. "
                "המתלוננת הציגה תיעוד של חודשיים: צילומים שצילם החשוד "
                "מרחוק, הודעות חוזרות ונשנות, והופעות ליד מקום עבודתה. "
                "הוגשה בקשה לצו הגנה."
            ),
            suspected_offense="הטרדה מאיימת",
            evidence_strength="חזקה — תיעוד מקיף, הודעות, צילומים",
            prior_record="אזהרה משטרתית על הפרת סדר ציבורי",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה מאוד — דפוס עקיבה מתועד",
            flight_risk_facts="נמוך — כתובת קבועה, עובד",
            police_request="הארכת מעצר 3 ימים",
            alternatives="צו הרחקה מיידי ומעצר בית",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D063: minimal ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D063",
            title="עבירת רכוש — חשד ראשוני",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר בסמוך לזירת פריצה לחנות. נמצא הולך ברחוב "
                "עם תיק גב. תוכן התיק טרם נבדק. אין עדי ראייה ישירים."
            ),
            suspected_offense="חשד לפריצה — טרם הוגדר",
            evidence_strength="חלשה — נסיבתית בלבד",
            prior_record="לא ידוע",
            weapon_status="לא נבדק",
            witness_contact_risk="לא ידוע",
            flight_risk_facts="לא ידוע — לא אומת מען",
            police_request="הארכת מעצר 2 ימים",
            alternatives="לא נבדקו חלופות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="minimal",
        ),
        # ── D064: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D064",
            title="ניסיון הברחת סמים בגבול — מעבר גבול",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר במעבר גבול כשברכבו נמצאו 5 ק\"ג קוקאין "
                "מוסתרים בתא כפול מתחת למושב האחורי. החשוד, אזרח ישראלי, "
                "חזר מירדן. טוען שלא ידע על הסמים ושאדם אחר ביקש ממנו "
                "להחזיר את הרכב. הסמים בשווי מוערך של כ-2 מיליון ש\"ח."
            ),
            suspected_offense="הברחת סמים מסוכנים",
            evidence_strength="חזקה מאוד — סמים ברכב החשוד, תא כפול מתוכנן",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני — חשש לתיאום עם שותפים",
            flight_risk_facts="גבוה — קשרים בירדן, דרכון בתוקף",
            police_request="הארכת מעצר 15 ימים",
            alternatives="איסור יציאה מהארץ, מסירת דרכון",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D065: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D065",
            title="תקיפה מינית — עובד במקום עבודה",
            legal_area="arrest_extension",
            base_facts_he=(
                "עובדת הגישה תלונה על תקיפה מינית של מנהלה בעבודה. "
                "לטענתה, במספר הזדמנויות ביצע מעשים מיניים ללא הסכמה. "
                "יש תכתובות מפלילות בטלפון. שתי עובדות נוספות מסרו "
                "עדויות על הטרדות דומות."
            ),
            suspected_offense="תקיפה מינית ומעשה מגונה",
            evidence_strength="בינונית-חזקה — תכתובות, עדויות תומכות",
            prior_record="לא ידוע",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה — החשוד מנהל את המתלוננות בעבודה",
            flight_risk_facts="נמוך — בעל עסק מקומי",
            police_request="הארכת מעצר 5 ימים",
            alternatives="צו הרחקה ממקום העבודה וממתלוננות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D066: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D066",
            title="החזקת חומרי נפץ — מחסן חקלאי",
            legal_area="arrest_extension",
            base_facts_he=(
                "במהלך חיפוש במחסן חקלאי של החשוד נמצאו חומרי נפץ "
                "בכמות משמעותית. החשוד, חקלאי, טוען שהחומרים משמשים "
                "לפיצוץ סלעים בשדה. אין לו רישיון להחזקת חומרי נפץ."
            ),
            suspected_offense="החזקת חומרי נפץ ללא היתר",
            evidence_strength="חזקה — חומרי נפץ נמצאו",
            prior_record="ללא הרשעות",
            weapon_status="חומרי נפץ — לא נשק קונבנציונלי",
            witness_contact_risk="נמוך",
            flight_risk_facts="נמוך — חקלאי עם קרקע באזור",
            police_request="הארכת מעצר 5 ימים",
            alternatives="מעצר בית ואיסור גישה למחסן",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D067: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D067",
            title="ערעור מעצר — עבירת סמים חמורה",
            legal_area="detention_appeal",
            base_facts_he=(
                "החשוד מגיש ערעור על החלטת בית משפט השלום להאריך מעצרו "
                "ב-10 ימים בחשד לסחר בסמים. נטען שנמצאו 2 ק\"ג הרואין "
                "בדירתו. הסנגור טוען שהחיפוש בוצע ללא צו ושהראיות פסולות. "
                "התביעה טוענת שהיה חשש מיידי להשמדת ראיות."
            ),
            suspected_offense="סחר בסמים מסוכנים — הרואין",
            evidence_strength="חזקה — סמים נתפסו, אך שאלת חוקיות החיפוש",
            prior_record="הרשעה בעבירות סמים לפני 6 שנים",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני",
            flight_risk_facts="בינוני — כתובת ידועה, אך עבר פלילי",
            police_request="דחיית הערעור והמשך המעצר",
            alternatives="מעצר בית בפיקוח אלקטרוני",
            procedural_posture="ערעור מעצר — דיון בבית משפט מחוזי",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D068: minimal ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D068",
            title="תקיפה — אירוע לא ברור",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר בעקבות תלונה על תקיפה. פרטי האירוע לא ברורים. "
                "המתלונן סירב לשתף פעולה עם המשטרה לאחר הגשת התלונה."
            ),
            suspected_offense="תקיפה — נסיבות לא ברורות",
            evidence_strength="חלשה מאוד — תלונה ללא שיתוף פעולה",
            prior_record="לא ידוע",
            weapon_status="לא הוערך",
            witness_contact_risk="לא ידוע",
            flight_risk_facts="לא הוערך",
            police_request="הארכת מעצר 2 ימים",
            alternatives="לא נבדקו",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="minimal",
        ),
        # ── D069: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D069",
            title="הברחת כלי נשק — רכב מסחרי",
            legal_area="arrest_extension",
            base_facts_he=(
                "במחסום משטרתי נעצר רכב מסחרי ובתוכו נמצאו שלושה אקדחים "
                "ותחמושת רבה מוסתרים מתחת לסחורה. הנהג טוען שאינו יודע "
                "על הנשק ושנשכר להוביל סחורה בלבד. בעל הרכב הוא אדם "
                "אחר שטרם אותר."
            ),
            suspected_offense="הברחת נשק וסחר בלתי חוקי בנשק",
            evidence_strength="חזקה — נשק ותחמושת ברכב שנהג",
            prior_record="עבירות תנועה חמורות",
            weapon_status="שלושה אקדחים ותחמושת",
            witness_contact_risk="בינוני — חשש לתיאום עם בעל הרכב",
            flight_risk_facts="לא הוערך",
            police_request="הארכת מעצר 10 ימים",
            alternatives="לא הוצעו בשל חומרת העבירה",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D070: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D070",
            title="עדות שקר בבית משפט — עד מרכזי",
            legal_area="arrest_extension",
            base_facts_he=(
                "עד מרכזי בתיק רצח נחשד במסירת עדות שקר בבית המשפט. "
                "ממצאי חקירה מראים סתירות חמורות בין עדותו לראיות "
                "אובייקטיביות. יש חשד שקיבל תשלום מהנאשם בתיק הרצח "
                "תמורת שינוי עדותו."
            ),
            suspected_offense="עדות שקר ושיבוש הליכי משפט",
            evidence_strength="בינונית — סתירות בעדות, חשד לתשלום",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה מאוד — חשש לתיאום עם הנאשם בתיק הרצח",
            flight_risk_facts="בינוני",
            police_request="הארכת מעצר 5 ימים",
            alternatives="צו איסור קשר עם הנאשם ועדים אחרים",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D071: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D071",
            title="ערעור מעצר — אלימות במשפחה חמורה",
            legal_area="detention_appeal",
            base_facts_he=(
                "החשוד מערער על מעצרו עד תום ההליכים בגין תקיפת בת זוגו "
                "שגרמה לשבר בלסת ולפגיעה ביד. הסנגור טוען שיש חלופת "
                "מעצר מתאימה — מעצר בית אצל הורי החשוד בעיר אחרת. "
                "התביעה טוענת שהחשוד הפר צו הרחקה קודם."
            ),
            suspected_offense="תקיפה הגורמת חבלה חמורה — אלימות במשפחה",
            evidence_strength="חזקה — תיעוד רפואי, הפרת צו קודם",
            prior_record="הרשעה קודמת באלימות במשפחה",
            weapon_status="ללא נשק — אלימות ידנית",
            witness_contact_risk="גבוה — היסטוריה של הפרת צווים",
            flight_risk_facts="נמוך — הורים מוכנים לערוב",
            police_request="דחיית הערעור — המשך מעצר עד תום ההליכים",
            alternatives="מעצר בית אצל הורים בעיר אחרת + פיקוח אלקטרוני",
            procedural_posture="ערעור מעצר — דיון בבית משפט מחוזי",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D072: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D072",
            title="הימורים לא חוקיים — הפעלת אתר הימורים",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר בחשד להפעלת אתר הימורים בלתי חוקי באינטרנט. "
                "מחזור ההימורים המוערך כ-5 מיליון ש\"ח בשנה. נמצאו "
                "שרתים ורישומי לקוחות בדירתו. החשוד טוען שהאתר פועל "
                "מחו\"ל ואינו כפוף לחוק הישראלי."
            ),
            suspected_offense="ניהול הימורים בלתי חוקיים",
            evidence_strength="חזקה — שרתים, רישומים, מחזור כספי",
            prior_record="ללא הרשעות",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="בינוני — קשרי עסקים בחו\"ל",
            police_request="הארכת מעצר 7 ימים",
            alternatives="ערבות כספית, איסור יציאה מהארץ",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D073: minimal ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D073",
            title="גרימת מוות בנהיגה — תאונה קטלנית",
            legal_area="arrest_extension",
            base_facts_he=(
                "נהג מעורב בתאונת דרכים קטלנית. הולך רגל נהרג. "
                "נסיבות התאונה טרם בוררו. החשוד נפצע קל ופונה לבית החולים."
            ),
            suspected_offense="גרימת מוות ברשלנות — תאונת דרכים",
            evidence_strength="ראשונית — טרם הושלמה חקירה תאונתית",
            prior_record="לא ידוע",
            weapon_status="לא רלוונטי",
            witness_contact_risk="לא ידוע",
            flight_risk_facts="לא הוערך — מאושפז",
            police_request="הארכת מעצר 3 ימים",
            alternatives="לא נבדקו",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="minimal",
        ),
        # ── D074: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D074",
            title="התעללות בקשיש — מטפל סיעודי",
            legal_area="arrest_extension",
            base_facts_he=(
                "מטפל סיעודי נחשד בהתעללות פיזית בקשיש בן 85 שטיפל בו. "
                "בן המשפחה התקין מצלמה נסתרת שתיעדה את המטפל מכה "
                "את הקשיש ומזניח את צרכיו. הקשיש אינו מסוגל למסור עדות "
                "בשל מצבו הקוגניטיבי."
            ),
            suspected_offense="התעללות בחסר ישע",
            evidence_strength="חזקה — צילום וידאו מפורש",
            prior_record="לא ידוע — עובד זר, קשה לבדוק",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך — הקשיש אינו מסוגל להעיד",
            flight_risk_facts="גבוה — אזרח זר, ויזה עומדת לפוג",
            police_request="הארכת מעצר 5 ימים",
            alternatives="מעצר בית ומסירת דרכון",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D075: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D075",
            title="ערעור מעצר — שוד מזוין חוזר",
            legal_area="detention_appeal",
            base_facts_he=(
                "החשוד מערער על מעצרו עד תום ההליכים בגין שני שודות "
                "מזוינים בחנויות נוחות. הוגש כתב אישום מפורט. "
                "הסנגור טוען שהודאת החשוד ניתנה תחת לחץ ושהזיהוי "
                "הפוטוגרפי לקוי. התביעה מציגה ראיות DNA ומצלמות."
            ),
            suspected_offense="שוד מזוין — שני אירועים",
            evidence_strength="חזקה מאוד — DNA, מצלמות, הודאה",
            prior_record="הרשעות בשוד ובגניבה",
            weapon_status="סכין — בשני האירועים",
            witness_contact_risk="נמוך",
            flight_risk_facts="גבוה — ללא כתובת קבועה, עבר פלילי עשיר",
            police_request="דחיית הערעור",
            alternatives="לא הוצעו חלופות בשל מסוכנות גבוהה",
            procedural_posture="ערעור מעצר — דיון בבית משפט מחוזי",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        # ── D076: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D076",
            title="הפרעה סדרי דין — בריחה ממעצר בית",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד שהיה במעצר בית בפיקוח אלקטרוני נמלט מביתו. "
                "אותר כעבור 3 ימים בעיר אחרת. טוען שהמעצר לא נסבל "
                "ושיצא לקנות תרופות. הפיקוח האלקטרוני תיעד את יציאתו."
            ),
            suspected_offense="הפרעה לסדרי דין — הפרת תנאי מעצר",
            evidence_strength="חזקה — פיקוח אלקטרוני תיעד את הבריחה",
            prior_record="נאשם בתיק תקיפה — העבירה המקורית",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני",
            flight_risk_facts="גבוה — כבר ברח ממעצר בית",
            police_request="הארכת מעצר בפועל 7 ימים",
            alternatives="לא הוצעו — הפר חלופה קודמת",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D077: minimal ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D077",
            title="חשד לעבירה — מידע מודיעיני בלבד",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר על בסיס מידע מודיעיני בלבד. טיב העבירה "
                "לא פורט בשלב זה. החשוד מכחיש כל מעורבות בפעילות "
                "בלתי חוקית."
            ),
            suspected_offense="טרם הוגדרה — חקירה בשלב ראשוני",
            evidence_strength="חלשה — מידע מודיעיני בלבד",
            prior_record="לא ידוע",
            weapon_status="לא נבדק",
            witness_contact_risk="לא ידוע",
            flight_risk_facts="לא הוערך",
            police_request="הארכת מעצר 2 ימים",
            alternatives="לא נבדקו חלופות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="minimal",
        ),
        # ── D078: partial ───────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D078",
            title="עבירות בנייה — בנייה ללא היתר בשטח ציבורי",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר בחשד לבניית מבנה מסחרי ללא היתר על שטח "
                "ציבורי. צו הריסה מנהלי הוצא אך לא בוצע. החשוד המשיך "
                "בבנייה בניגוד לצו. יש תיעוד צילומי של ההתקדמות בבנייה."
            ),
            suspected_offense="בנייה ללא היתר והפרת צו הריסה",
            evidence_strength="חזקה — צו הריסה שהופר, תיעוד צילומי",
            prior_record="עבירת בנייה קודמת — קנס",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="נמוך — בעל עסק מקומי",
            police_request="הארכת מעצר 3 ימים",
            alternatives="ערבות כספית והתחייבות להפסקת הבנייה",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        # ── D079: minimal ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D079",
            title="הונאת ביטוח — תביעה כוזבת",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר בחשד להגשת תביעת ביטוח כוזבת על אירוע שלא "
                "התרחש. חברת הביטוח העבירה חשד למשטרה. החקירה בשלב ראשוני."
            ),
            suspected_offense="קבלת דבר במרמה — הונאת ביטוח",
            evidence_strength="ראשונית — חשד חברת ביטוח",
            prior_record="לא ידוע",
            weapon_status="לא רלוונטי",
            witness_contact_risk="לא הוערך",
            flight_risk_facts="לא ידוע",
            police_request="הארכת מעצר 3 ימים",
            alternatives="לא נבדקו",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="minimal",
        ),
        # ── D080: complete ──────────────────────────────────────────────
        DetentionBaseCase(
            case_id="D080",
            title="פעילות ארגון פשיעה — ראש רשת",
            legal_area="post_indictment_remand",
            base_facts_he=(
                "הוגש כתב אישום מפורט נגד החשוד כראש רשת פשיעה מאורגנת. "
                "כתב האישום כולל עבירות סחר בסמים, סחיטה, הלבנת הון, "
                "והחזקת נשק. חקירה ממושכת של שנתיים כללה האזנות סתר "
                "וסוכן סמוי. יש עדי מדינה ותיעוד נרחב. "
                "החשוד מיוצג על ידי צוות סנגורים ומכחיש הכל."
            ),
            suspected_offense="עמידה בראש ארגון פשיעה, סחר בסמים, סחיטה, הלבנת הון",
            evidence_strength="חזקה מאוד — האזנות סתר, עדי מדינה, סוכן סמוי",
            prior_record="הרשעות בעבירות אלימות ורכוש",
            weapon_status="נשק נתפס בחיפושים — אקדחים ורובה",
            witness_contact_risk="גבוה מאוד — עדי מדינה בסכנה",
            flight_risk_facts="גבוה מאוד — הון רב, קשרים בינלאומיים, דרכונים",
            police_request="מעצר עד תום ההליכים",
            alternatives="לא הוצעו חלופות — מסוכנות גבוהה",
            procedural_posture="לאחר הגשת כתב אישום — בקשה למעצר עד תום ההליכים",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
    ]
