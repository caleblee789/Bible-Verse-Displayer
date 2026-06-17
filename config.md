# Bible Verse Displayer

Display an encouraging Bible verse on Anki's deck browser screen.

## Configuration

You can now open **Tools → Bible Verse Display Settings → Open Bible Verse Display Settings**
to edit settings in a dedicated dialog.

- **Default translation:** The bundled default list contains 483 entries covering 500 quoted verses from the New Living Translation (NLT).
  - Default verse references are marked with `(NLT)`.
- **Verses:** Add one or more verses/messages as HTML strings.
  - You can use HTML tags like `&lt;br&gt;` for line breaks.
  - Use **Import** and **Export** to move verse lists in `.txt` or `.json` format.
  - The settings dialog shows a verse count and a live preview before saving.
- **Rotation mode:** Choose how often the displayed verse changes.
  - `daily` keeps one verse for the day.
  - `every render` chooses again whenever Anki redraws the deck browser.
  - `manual` keeps the current verse until settings are saved again.
- **Font color:** A valid CSS color value (for example `#1E90FF`, `rgb(30,144,255)`, or named colors like `dodgerblue`).
  - When **Use theme-aware color** is enabled, the add-on automatically chooses readable colors for light and dark themes.
- **Font family:** A plain CSS font-family string. Unsafe characters like quotes, `<`, `>`, or `;` are ignored.
- **Font size:** Must include a unit and be in range:
  - `px` from `8` to `96`
  - `em`/`rem` from `0.5` to `6`
  - `%` from `50` to `300`

## Scripture Attribution

Scripture quotations are taken from the Holy Bible, New Living Translation,
copyright ©1996, 2004, 2015 by Tyndale House Foundation. Used by permission
of Tyndale House Publishers, Carol Stream, Illinois 60188. All rights reserved.
