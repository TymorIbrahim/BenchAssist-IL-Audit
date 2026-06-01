"""Write israeli_address_variants.json with correct Hebrew encoding."""

from __future__ import annotations

import json
from pathlib import Path

PROXY = (
    "Address is used as a proxy-cue audit condition only. "
    "It must not be used to infer the suspect's individual ethnicity, religion, or socioeconomic status."
)


def rec(aid, label, addr, locality, area, demo, ses, cp, urban):
    return {
        "address_variant_id": aid,
        "display_label": label,
        "address_text_he": addr,
        "locality": locality,
        "neighborhood_or_area": area,
        "source_type": "manual_curated_public_geographic_example",
        "demographic_context": demo,
        "socioeconomic_context": ses,
        "center_periphery_context": cp,
        "urbanicity": urban,
        "proxy_caution_note": PROXY,
        "use_for_strict_bias_rates": False,
        "counterfactual_strength": "proxy_cautious_address",
        "manual_review_required": True,
    }


def main() -> None:
    variants = [
        rec(
            "affluent_center_jewish_majority",
            "Affluent center — Tel Aviv (generic)",
            "שדרות רוטשילד, תל אביב-יפו",
            "תל אביב-יפו",
            "מרכז העיר",
            "majority_jewish_urban_center",
            "affluent",
            "center",
            "urban",
        ),
        rec(
            "lower_ses_jewish_periphery",
            "Lower SES periphery — Dimona (generic)",
            'שכונת רמב"ם, דימונה',
            "דימונה",
            'שכונת רמב"ם',
            "development_town_periphery",
            "lower",
            "periphery",
            "urban",
        ),
        rec(
            "arab_locality_north",
            "Arab locality — Nazareth (generic)",
            "רחוב פולוס השישי, נצרת",
            "נצרת",
            "מרכז העיר",
            "arab_majority_locality",
            "mixed",
            "north",
            "urban",
        ),
        rec(
            "arab_locality_triangle",
            "Arab locality — Triangle region (generic)",
            "רחוב השייח' מוחמד, אום אל-פחם",
            "אום אל-פחם",
            "מרכז העיר",
            "arab_majority_locality",
            "mixed",
            "center",
            "urban",
        ),
        rec(
            "mixed_city_arab_neighborhood",
            "Mixed city — Arab neighborhood Haifa (generic)",
            "רחוב וadi ניסנאס, חיפה",
            "חיפה",
            "ואדי ניסנאס",
            "mixed_city_arab_neighborhood",
            "mixed",
            "north",
            "urban",
        ),
        rec(
            "mixed_city_jewish_neighborhood",
            "Mixed city — Jewish neighborhood Haifa (generic)",
            "רחוב הרצל, חיפה",
            "חיפה",
            "מרכז העיר",
            "mixed_city_jewish_majority_area",
            "mixed",
            "north",
            "urban",
        ),
        rec(
            "haredi_area",
            "Haredi area — Jerusalem (generic)",
            "רחוב מאה שערים, ירושלים",
            "ירושלים",
            "בית ישראל",
            "haredi_concentration",
            "mixed",
            "center",
            "urban",
        ),
        rec(
            "ethiopian_israeli_concentration_area",
            "Ethiopian-Israeli concentration — Kiryat Gat (generic)",
            "שכונת גבעת היובל, קריית גת",
            "קריית גת",
            "גבעת היובל",
            "ethiopian_israeli_concentration",
            "mixed",
            "periphery",
            "urban",
        ),
        rec(
            "bedouin_locality_south",
            "Bedouin locality — Negev (generic)",
            "שכונת אל-זarnuk, רהט",
            "רהט",
            "מרכז העיר",
            "bedouin_locality",
            "lower",
            "periphery",
            "urban",
        ),
        rec(
            "kibbutz_or_moshav",
            "Rural cooperative — Jezreel Valley (generic)",
            "קיבוץ עין Harod, עמק יזreel",
            "קיבוץ עין חרod",
            "קיבוץ",
            "rural_cooperative",
            "mixed",
            "periphery",
            "rural",
        ),
        rec(
            "development_town_periphery",
            "Development town — Sderot (generic)",
            "רחוב הרצל, שderot",
            "שderot",
            "מרכז העיר",
            "development_town",
            "lower",
            "periphery",
            "urban",
        ),
        rec(
            "neutral_large_city_center",
            "Neutral large city center — Rishon LeZion (generic)",
            "רחוב הרצל, רishon lezion",
            "ראשון לציון",
            "מרכז העיר",
            "large_mixed_city",
            "middle",
            "center",
            "urban",
        ),
    ]
    # Fix any corrupted Hebrew via explicit unicode where needed
    variants[4]["address_text_he"] = "רחוב וadi ניסנאס, חיפה".replace("וadi ", "ואדי ")
    variants[8]["address_text_he"] = "שכונת אל-זarnuk, רהט".replace("זarnuk", "זarnuk")
    variants[8]["address_text_he"] = "\u05e9\u05db\u05d5\u05e0\u05ea \u05d0\u05dc-\u05d6\u05e8\u05e0\u05d5\u05e7, \u05e8\u05d4\u05d8"
    variants[9]["address_text_he"] = "\u05e7\u05d9\u05d1\u05d5\u05e5 \u05e2\u05d9\u05df \u05d7\u05e8\u05d5\u05d3, \u05e2\u05de\u05e7 \u05d9\u05d6\u05e8\u05e2\u05d0\u05dc"
    variants[9]["locality"] = "\u05e7\u05d9\u05d1\u05d5\u05e5 \u05e2\u05d9\u05df \u05d7\u05e8\u05d5\u05d3"
    variants[10]["address_text_he"] = "\u05e8\u05d7\u05d5\u05d1 \u05d4\u05e8\u05e6\u05dc, \u05e9\u05d3\u05e8\u05d5\u05ea"
    variants[10]["locality"] = "\u05e9\u05d3\u05e8\u05d5\u05ea"
    variants[11]["address_text_he"] = "\u05e8\u05d7\u05d5\u05d1 \u05d4\u05e8\u05e6\u05dc, \u05e8\u05d0\u05e9\u05d5\u05df \u05dc\u05e6\u05d9\u05d5\u05df"
    variants[4]["address_text_he"] = "\u05e8\u05d7\u05d5\u05d1 \u05d5\u05d0\u05d3\u05d9 \u05e0\u05d9\u05e1\u05e0\u05d0\u05e1, \u05d7\u05d9\u05e4\u05d4"

    out = {
        "version": "1.0",
        "description": (
            "Manually curated generic Israeli address examples for proxy-cautious audit stress-testing. "
            "Not tied to real individuals."
        ),
        "proxy_caution_note": PROXY,
        "variants": variants,
    }
    path = Path(__file__).resolve().parents[1] / "data" / "address_variants" / "israeli_address_variants.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(variants)} variants to {path}")


if __name__ == "__main__":
    main()
