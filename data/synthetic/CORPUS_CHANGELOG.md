# Synthetic detention corpus changelog

## detention_slim_v1 (1.0.0)

- Slim variant set (7 core + 6 address-proxy per base when enabled).
- Default pilot scale: 10 base cases (`D001`–`D010`).
- Address-proxy variants use `proxy_cautious_address` strength; excluded from strict headline rates.
- Neutral rows may include neutral address control line when address variants are generated for the base.
- Output schema target: `detention_minimal_dangerousness_v2`.

### When to bump version

- Variant prompt text or fact blocks change.
- Address registry (`data/address_variants/israeli_address_variants.json`) changes.
- Strict vs strict-excluded classification rules change.

After bumping, regenerate CSV and re-run validity + Gemini preflight.
