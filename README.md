# Bible Verse Displayer

Display an encouraging Bible verse at the bottom of Anki's deck browser.

## Features

- 483 default entries covering 500 quoted verses from the New Living Translation (NLT).
- Theme-aware display colors for readable light-mode and night-mode rendering.
- Responsive quote-card layout for long passages.
- Settings dialog for editing verses, import/export, font choices, and rotation mode.
- Daily, every-render, and manual rotation modes.

## Installation

Install from AnkiWeb:

<https://ankiweb.net/shared/info/290511870>

For local testing, copy this folder into Anki's add-ons folder or install the release artifact from `dist/`.

## Configuration

Open **Tools -> Bible Verse Display Settings -> Open Bible Verse Display Settings** in Anki.

The bundled defaults use the New Living Translation. Default references are marked with `(NLT)`.

## Development

Run the local checks:

```sh
python3 -m unittest tests/test_ui_rendering.py
env PYTHONPYCACHEPREFIX=/private/tmp/bibleverses-pycache python3 -m py_compile __init__.py config.py tests/test_ui_rendering.py tools/build_ankiaddon.py
python3 -m json.tool config.json
```

Build an Anki add-on artifact:

```sh
python3 tools/build_ankiaddon.py
```

The generated `.ankiaddon` file is written to `dist/`.

## Scripture Attribution

Scripture quotations are taken from the Holy Bible, New Living Translation,
copyright ©1996, 2004, 2015 by Tyndale House Foundation. Used by permission
of Tyndale House Publishers, Carol Stream, Illinois 60188. All rights reserved.

The bundled defaults are capped at 500 quoted Bible verses without express written permission.

## License

This add-on is licensed under the GNU Affero General Public License v3.0 or later.
