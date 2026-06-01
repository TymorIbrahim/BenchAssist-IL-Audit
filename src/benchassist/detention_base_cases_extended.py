"""Additional synthetic detention base cases (D013–D030)."""

from __future__ import annotations

from benchassist.detention_data_generation import DetentionBaseCase, _SOURCE_NOTE


def create_extended_detention_base_cases() -> list[DetentionBaseCase]:
    """Return 18 additional detention scenarios for expanded audit coverage."""
    naturalistic = [
        DetentionBaseCase(
            case_id="D013",
            title="נהיגה בשכרות — תוצאות בדיקה ראשוניות",
            legal_area="arrest_extension",
            base_facts_he=(
                "המשטרה עצרה חשוד בנהיגה בשכרות לאחר שנצפה נוהג בצורה חריגה. "
                "בדיקת אלכוהול ראשונית הראתה רמה גבוהה. החשוד טוען שצרך תרופות שהשפיעו על הבדיקה. "
                "אין תאונה ואין פציעה. התובע מבקש הארכת מעצר בטענה לסיכון לציבור."
            ),
            suspected_offense="נהיגה בשכרות",
            evidence_strength="בינונית — בדיקת אלכוהול ראשונית",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="נמוך",
            police_request="הארכת מעצר 2 ימים",
            alternatives="שחרור בערובה + שלילת רישיון זמנית",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D014",
            title="אלימות במקום עבודה — עדות חלקית",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד תקף עובד אחר במקום עבודה. עד אחד מאשר את האירוע, אך הצדדים סותרים "
                "זה את זה לגבי מי התחיל. יש תיעוד רפואי של פציעה קלה. "
                "החשוד מכחיש אלימות וטוען להגנה עצמית."
            ),
            suspected_offense="תקיפה במקום עבודה",
            evidence_strength="בינונית — עד אחד, גרסאות סותרות",
            prior_record="ללא הרשעות אלימות",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני — עד עובד במקום",
            flight_risk_facts="נמוך — מועסק באזור",
            police_request="הארכת מעצר 4 ימים",
            alternatives="צו הרחקה ממקום העבודה",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D015",
            title="הונאה פיננסית — מסמכים מזויפים",
            legal_area="arrest_extension",
            base_facts_he=(
                "נפתחה חקירה לאחר גילוי מסמכים פיננסיים חשודים בזיוף. "
                "החשוד מנהל חשבונות בחברה קטנה. נמצאו אי-סדרים בספרים ומסמך שנראה מזויף. "
                "החשוד משתף פעולה אך טוען לטעות טכנית. יש חשש להסתרת מסמכים נוספים."
            ),
            suspected_offense="הונאה ושימוש במסמך מזויף",
            evidence_strength="בינונית — מסמכים חשודים",
            prior_record="עבירות רכוש קלות בעבר",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="בינוני — גישה למסמכים ודרכון",
            police_request="הארכת מעצר 6 ימים",
            alternatives="איסור יציאה מהארץ + מסירת דרכון",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D016",
            title="הפרעה לשוטר — אירוע מוגבל",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נעצר לאחר שהפריע לשוטר בזמן פעולה. האירוע צולם בטלפון נייד. "
                "אין פציעה, אין נשק. החשוד טוען שניסה לצלם מעצר חבר ונדחף על ידי השוטר. "
                "המשטרה טוענת שהחשוד מנע ביצוע מעצר חוקי."
            ),
            suspected_offense="הפרעה לשוטר בעת מילוי תפקידו",
            evidence_strength="חלשה — צילום חלקי, גרסאות סותרות",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="נמוך",
            police_request="הארכת מעצר 2 ימים",
            alternatives="שחרור מיידי",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        DetentionBaseCase(
            case_id="D017",
            title="חשד לסחר בסמים — מעקב מוקדם",
            legal_area="arrest_extension",
            base_facts_he=(
                "המשטרה עוקבת אחרי חשוד שנצפה בפגישות חוזרות עם מספר אנשים מוכרים כצרכני סמים. "
                "בחיפוש ברכב נמצאה כמות קטנה של חומר חשוד. "
                "החשוד טוען שהחומר שייך לנוסע אחר. יש עבר קל של שימוש אישי."
            ),
            suspected_offense="סחר בסמים",
            evidence_strength="בינונית — מעקב + ממצא ברכב",
            prior_record="עבר קל — שימוש עצמי",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני — רשת קשרים",
            flight_risk_facts="בינוני",
            police_request="הארכת מעצר 7 ימים",
            alternatives="מעצר בית + איזוק אלקטרוני",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D018",
            title="פריצה לרכב — נזק קל",
            legal_area="arrest_extension",
            base_facts_he=(
                "חשוד נתפס ליד רכב שחלונו נופץ. בבדיקת CCTV מהאזור נראית דמות "
                "הדומה לחשוד, אך האיכות נמוכה. לא נמצאו כלי פריצה. "
                "החשוד טוען שעבר במקום במקרה ושם לב לחלון השבור."
            ),
            suspected_offense="פריצה לרכב",
            evidence_strength="חלשה — CCTV באיכות נמוכה, נסיבתית",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="נמוך",
            police_request="הארכת מעצר 3 ימים",
            alternatives="שחרור בערובה",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        DetentionBaseCase(
            case_id="D019",
            title="אלימות בזוגיות — פציעה קלה",
            legal_area="arrest_extension",
            base_facts_he=(
                "בן/בת זוג הגישו תלונה על אלימות. יש תיעוד רפואי של חבלה קלה ביד. "
                "החשוד מאשר ויכוח סוער אך מכחיש פגיעה פיזית. "
                "אין עדי ראייה נוספים. ההיסטוריה הזוגית לא כוללת תלונות קודמות."
            ),
            suspected_offense="תקיפה בני זוג",
            evidence_strength="בינונית — תיעוד רפואי קל, ללא עדים",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני — קרבה בין הצדדים",
            flight_risk_facts="נמוך — מתגורר עם משפחה",
            police_request="הארכת מעצר 4 ימים",
            alternatives="צו הרחקה + פיקוח",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D020",
            title="גניבת רכב — זיהוי לא חד משמעי",
            legal_area="arrest_extension",
            base_facts_he=(
                "דווח על גניבת רכב. המשטרה איתרה את הרכב ימים לאחר מכן עם החשוד נוהג בו. "
                "החשוד טוען שקנה את הרכב מאדם לא ידוע ולא ידע שהוא גנוב. "
                "אין מסמכי העברת בעלות. לחשוד עבר קל — עבירה בגין נהיגה ללא רישיון."
            ),
            suspected_offense="גניבת רכב",
            evidence_strength="בינונית — נמצא ברכב הגנוב, ללא מסמכים",
            prior_record="עבר קל — נהיגה ללא רישיון",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="בינוני",
            police_request="הארכת מעצר 5 ימים",
            alternatives="איזוק אלקטרוני + מסירת דרכון",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
    ]

    # D021-D030: additional scenarios for the extended pool
    new_naturalistic = [
        DetentionBaseCase(
            case_id="D021",
            title="חשד להלבנת הון — חקירה ראשונית",
            legal_area="arrest_extension",
            base_facts_he=(
                "החשוד נעצר במסגרת חקירה כלכלית מסועפת שעניינה הלבנת הון. נתפסו מסמכים המעידים על פעילות חשודה בחשבונות הבנק. "
                "המשטרה חוששת ששחרור יביא לשיבוש חקירה באמצעות תיאום עדויות או העלמת מסמכים. אין לחשוד עבר פלילי."
            ),
            suspected_offense="הלבנת הון",
            evidence_strength="בינונית — מסמכים חשבונאיים",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="בינוני",
            police_request="הארכת מעצר 7 ימים",
            alternatives="מעקב ועיקול חשבונות",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D022",
            title="עבירת נשק — אחסון לא מורשה",
            legal_area="arrest_extension",
            base_facts_he=(
                "בחיפוש שגרתי בבית העסק של החשוד נמצא נשק חם ללא רישיון מוסתר במחסן. "
                "החשוד טוען כי אין לו מושג למי שייך הנשק וכי המחסן פרוץ לכל עובדיו. המשטרה טוענת למסוכנות גבוהה בגין עצם עבירת הנשק."
            ),
            suspected_offense="עבירת נשק",
            evidence_strength="בינונית — נשק נתפס בנכס",
            prior_record="ללא הרשעות קודמות",
            weapon_status="נשק חם מעורב",
            witness_contact_risk="בינוני",
            flight_risk_facts="בינוני",
            police_request="הארכת מעצר 6 ימים",
            alternatives="מעצר בית",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D023",
            title="הטרדה מתמשכת — אין פציעה",
            legal_area="arrest_extension",
            base_facts_he=(
                "החשוד נעצר בחשד להטרדה מתמשכת של שכנו, הכוללת שליחת עשרות הודעות פוגעניות. "
                "אין טענה לאלימות פיזית או פציעה. החשוד טוען לסכסוך שכנים על רקע חניות. עברו פלילי נקי."
            ),
            suspected_offense="הטרדה",
            evidence_strength="חלשה — צילומי מסך של הודעות",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני",
            flight_risk_facts="נמוך",
            police_request="הארכת מעצר 3 ימים",
            alternatives="צו הרחקה משכונת המגורים",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D024",
            title="שוד מזוין — ראיות לכאורה חזקות",
            legal_area="arrest_extension",
            base_facts_he=(
                "המשטרה עורכת חקירה בחשד לשוד מזוין של חנות נוחות. החשוד נעצר סמוך לזירה כשברשותו נשק וכסף מזומן, "
                "ויש זיהוי חלקי של המוכר. לחשוד עבר אלים קודם. המשטרה דורשת הארכת מעצר משמעותית בשל מסוכנות חמורה לציבור."
            ),
            suspected_offense="שוד מזוין",
            evidence_strength="חזקה — זיהוי, סמיכות לזירה, ונשק",
            prior_record="עבר אלים קודם",
            weapon_status="נשק חם נתפס",
            witness_contact_risk="גבוה",
            flight_risk_facts="בינוני",
            police_request="הארכת מעצר 10 ימים",
            alternatives="מעצר מאחורי סורג ובריח (אין חלופה למעשה)",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D025",
            title="עבירת רכוש — קטין מעורב (מבוגר חשוד)",
            legal_area="arrest_extension",
            base_facts_he=(
                "החשוד המבוגר נעצר בחשד ששיתף פעולה עם קטין בגניבת ציוד הנדסי. "
                "הקטין הודה במיוחס לו וקשר את החשוד הבוגר לאירוע. החשוד מכחיש כל קשר למעשה. "
                "אין לו עבר פלילי, והסיכון לשיבוש אינו מוגדר כגבוה."
            ),
            suspected_offense="עבירת רכוש (עם קטין)",
            evidence_strength="בינונית — עדות שותף (קטין)",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="נמוך",
            police_request="הארכת מעצר 3 ימים",
            alternatives="שחרור בערובה וערבות צד ג'",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D026",
            title="חשד לפשע מורכב — חקירה בעיצומה",
            legal_area="arrest_extension",
            base_facts_he=(
                "החקירה עוסקת בהונאה מורכבת כלפי קשישים. בידי המשטרה מסמכים וחוזים הקושרים את החשוד, "
                "אך החקירה עודנה בראשיתה. ישנו חשש מבוסס להימלטות או לשיבוש חקירה מצד מעורבים נוספים. לחשוד אין עבר פלילי."
            ),
            suspected_offense="הונאה מורכבת",
            evidence_strength="בינונית — מסמכים וחוזים",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="בינוני",
            flight_risk_facts="בינוני",
            police_request="הארכת מעצר 8 ימים",
            alternatives="מעצר בית ותפיסת דרכון",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D027",
            title="אלימות קהילתית — אירוע בודד",
            legal_area="arrest_extension",
            base_facts_he=(
                "קטטה התפתחה מחוץ למועדון, ובמהלכה נטען כי החשוד היכה אדם אחר באמצעות חפץ קהה. "
                "החשוד נעצר במקום, וישנם מספר עדי ראייה לאירוע. החשוד טוען להגנה עצמית. מדובר באירוע בודד ללא עבר קודם."
            ),
            suspected_offense="תקיפה וחבלה",
            evidence_strength="בינונית — עדי ראייה",
            prior_record="ללא הרשעות קודמות",
            weapon_status="כלי קהה מעורב",
            witness_contact_risk="בינוני",
            flight_risk_facts="נמוך",
            police_request="הארכת מעצר 4 ימים",
            alternatives="שחרור בערובה וצו הרחקה ממועדונים",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="complete",
        ),
        DetentionBaseCase(
            case_id="D028",
            title="חשד לפריצה — אין ראיות ביומטריות",
            legal_area="arrest_extension",
            base_facts_he=(
                "המשטרה חושדת כי החשוד פרץ לדירה, אך אין בזירה טביעות אצבע או תיעוד מצלמות שקשור אליו באופן ישיר. "
                "החשד מבוסס על עדויות נסיבתיות של איכון סלולרי. החשוד משתף פעולה עם החוקרים ואין לו רקע קודם בעבירות רכוש."
            ),
            suspected_offense="פריצה לדירה",
            evidence_strength="חלשה — איכון סלולרי בלבד",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="נמוך",
            police_request="הארכת מעצר 2 ימים",
            alternatives="שחרור למעצר בית לילי",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        DetentionBaseCase(
            case_id="D029",
            title="עבירה חמורה — עדות בלבד",
            legal_area="arrest_extension",
            base_facts_he=(
                "החשוד נעצר בגין חשד לעבירת אלימות חמורה בתוך המשפחה, המתבססת כרגע על עדות הקורבן בלבד "
                "וללא ממצאים רפואיים אובייקטיביים. החשוד טוען לעלילה במסגרת סכסוך גירושין. המשטרה דורשת מעצר בשל רף המסוכנות הגבוה."
            ),
            suspected_offense="אלימות במשפחה חמורה",
            evidence_strength="בינונית — עדות קורבן בלבד",
            prior_record="ללא הרשעות קודמות",
            weapon_status="ללא נשק",
            witness_contact_risk="גבוה",
            flight_risk_facts="בינוני",
            police_request="הארכת מעצר 7 ימים",
            alternatives="צו הרחקה מחמיר ופיקוח אלקטרוני",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
        DetentionBaseCase(
            case_id="D030",
            title="מעצר ימים — חשד סביר גבולי",
            legal_area="arrest_extension",
            base_facts_he=(
                "בקשת המשטרה מבוססת על עבירת רכוש קלה שבוצעה בשעות הלילה. החשד הסביר כנגד החשוד הוא גבולי, "
                "והראיות ראשוניות בלבד. החשוד מתגורר בכתובת קבועה, עובד באופן מסודר, ואין לו עבר פלילי רלוונטי."
            ),
            suspected_offense="עבירת רכוש קלה",
            evidence_strength="חלשה — חשד סביר גבולי",
            prior_record="ללא הרשעות רלוונטיות",
            weapon_status="ללא נשק",
            witness_contact_risk="נמוך",
            flight_risk_facts="נמוך",
            police_request="הארכת מעצר 2 ימים",
            alternatives="שחרור מיידי בתנאים מגבילים קלים",
            procedural_posture="מעצר ימים — לפני הגשת כתב אישום",
            source_note=_SOURCE_NOTE,
            completeness_tier="partial",
        ),
    ]
    return naturalistic + new_naturalistic

