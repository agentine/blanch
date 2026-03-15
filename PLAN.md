# blanch — Drop-in Replacement for bleach

**Package name:** blanch (verified available on PyPI)
**Language:** Python 3.10+
**Replaces:** mozilla/bleach (52.4M downloads/month, deprecated Jan 2023)

## Problem

bleach is the de facto HTML sanitization library for Python with 52.4M monthly downloads, 2.8k stars, and 17k+ dependents. Mozilla deprecated it in January 2023 because it depends on html5lib, which is also unmaintained. The recommended alternative (nh3) has a fundamentally different API and lacks linkify support, requiring full rewrites to migrate. No maintained drop-in replacement exists.

## Solution

blanch provides bleach's full API with modern internals:
- Same function signatures (`clean`, `linkify`)
- Same class APIs (`Cleaner`, `Linker`, `CSSSanitizer`)
- Same default constants (`ALLOWED_TAGS`, `ALLOWED_ATTRIBUTES`, `ALLOWED_PROTOCOLS`)
- Zero dependencies — uses `html.parser` from stdlib instead of html5lib
- Drop-in compatibility layer (`blanch.compat.bleach`)

## Architecture

### Core Components

1. **HTML Parser** (`blanch/parser.py`)
   - Built on `html.parser.HTMLParser` from stdlib
   - Tokenizer that emits start/end/comment/data/entity events
   - Handles malformed HTML gracefully (self-closing tags, missing end tags, attribute edge cases)
   - Security-focused: normalizes entities, strips null bytes, handles nesting limits

2. **Sanitizer** (`blanch/sanitizer.py`)
   - `clean(text, tags, attributes, protocols, strip, strip_comments, css_sanitizer)` — top-level function
   - `Cleaner` class — reusable sanitizer instance
   - Allowlist-based: only permitted tags/attributes/protocols pass through
   - Disallowed tags are either escaped (`&lt;script&gt;`) or stripped
   - Attribute values validated against protocol allowlist for URL attributes (href, src, etc.)
   - `filters` parameter for post-processing pipeline

3. **Linkifier** (`blanch/linkifier.py`)
   - `linkify(text, callbacks, skip_tags, parse_email)` — top-level function
   - `Linker` class — reusable linkifier instance
   - URL detection via configurable regex
   - Email detection with optional toggle
   - Callback system for modifying generated `<a>` tag attributes
   - `DEFAULT_CALLBACKS` with `nofollow` callback
   - `build_url_re(tlds, protocols)` and `build_email_re(tlds)` helpers
   - HTML-aware: skips content inside specified tags (e.g. `<pre>`, `<code>`)

4. **CSS Sanitizer** (`blanch/css_sanitizer.py`)
   - `CSSSanitizer(allowed_css_properties, allowed_svg_properties)` class
   - Strips disallowed CSS properties from `style` attributes
   - Validates CSS values (no url(), no expression(), no javascript:)

5. **Constants** (`blanch/constants.py`)
   - `ALLOWED_TAGS` — frozenset of safe HTML tags (a, abbr, acronym, b, blockquote, code, em, i, li, ol, strong, ul)
   - `ALLOWED_ATTRIBUTES` — dict mapping tags to permitted attribute lists
   - `ALLOWED_PROTOCOLS` — frozenset({'http', 'https', 'mailto'})

6. **Compatibility Layer** (`blanch/compat/bleach.py`)
   - Module that re-exports all public APIs matching `import bleach` interface
   - `bleach.clean`, `bleach.linkify`, `bleach.sanitizer.Cleaner`, etc.
   - Users can alias: `import blanch.compat.bleach as bleach`

### Package Structure

```
blanch/
├── __init__.py          # Public API: clean, linkify, Cleaner, Linker, constants
├── parser.py            # HTML tokenizer/parser (stdlib html.parser based)
├── sanitizer.py         # Cleaner class, clean() function, BleachSanitizerFilter compat
├── linkifier.py         # Linker class, linkify() function, callbacks, regex builders
├── css_sanitizer.py     # CSSSanitizer class
├── constants.py         # ALLOWED_TAGS, ALLOWED_ATTRIBUTES, ALLOWED_PROTOCOLS
├── compat/
│   ├── __init__.py
│   └── bleach.py        # Drop-in bleach module replacement
└── py.typed             # PEP 561 marker
```

### Key Design Decisions

- **Zero dependencies**: stdlib `html.parser` instead of html5lib. Trades HTML5 spec conformance for independence and performance. bleach's security model is allowlist-based, so parser spec conformance matters less than in a full browser.
- **Type annotations**: Full typing with `py.typed` marker for mypy/pyright.
- **Python 3.10+**: Modern Python only. No Python 2 compat.
- **ESM-style**: Single `blanch` package with submodules, not flat namespace.

## Deliverables

1. Core HTML parser with security hardening
2. Sanitizer with full bleach.clean() API compatibility
3. Linkifier with full bleach.linkify() API compatibility
4. CSS sanitizer
5. Drop-in bleach compatibility layer
6. Comprehensive test suite (including bleach's own test cases)
7. Published to PyPI as `blanch`

## Test Strategy

- Port bleach's existing test suite (MIT-licensed) as baseline
- Add edge case tests for malformed HTML, XSS vectors, entity handling
- Test compatibility layer against bleach's public API contracts
- Fuzz testing with known XSS payloads (OWASP, XSS cheat sheets)
