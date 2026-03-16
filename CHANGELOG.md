# Changelog

## 0.1.0

Initial release — drop-in replacement for [bleach](https://github.com/mozilla/bleach).

- HTML parser/tokenizer with security hardening (null byte stripping, nesting depth limits)
- `Cleaner` class and `clean()` function matching `bleach.clean()` API
- `Linker` class and `linkify()` function matching `bleach.linkify()` API
- `CSSSanitizer` class for CSS property allowlisting
- Bleach compatibility layer (`blanch.compat.bleach`)
- Zero dependencies — uses stdlib `html.parser`
- Full type annotations (mypy strict)
- Python 3.10–3.13 support
