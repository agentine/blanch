# blanch

Drop-in replacement for [bleach](https://github.com/mozilla/bleach), the deprecated HTML sanitization library.

## Features

- Same API as bleach (`clean`, `linkify`, `Cleaner`, `Linker`, `CSSSanitizer`)
- Zero dependencies — uses `html.parser` from stdlib
- Python 3.10+
- Full type annotations

## Installation

```bash
pip install blanch
```

## Usage

```python
import blanch

# Sanitize HTML
blanch.clean("<script>alert('xss')</script><b>hello</b>")
# '&lt;script&gt;alert(\'xss\')&lt;/script&gt;<b>hello</b>'

# Linkify URLs
blanch.linkify("Visit https://example.com")
# 'Visit <a href="https://example.com" rel="nofollow">https://example.com</a>'
```

## Migrating from bleach

```python
# Option 1: Replace import
# Before: import bleach
import blanch as bleach

# Option 2: Use compatibility layer
import blanch.compat.bleach as bleach
```

## License

MIT
