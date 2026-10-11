---
name: ascii-art
description: "ASCII art: pyfiglet, cowsay, boxes, image-to-ascii."
version: 4.1.0
author: 0xbyt4, Hermes Agent
license: MIT
dependencies:
  optional:
    - cowsay       # Tool 3 — sudo apt install cowsay
    - boxes        # Tool 4 — sudo apt install boxes
    - toilet       # Tool 5 — sudo apt install toilet toilet-fonts (terminal-only, not Discord)
    - ascii-image-converter  # Tool 6 — sudo snap install ascii-image-converter
    - jp2a         # Tool 6 alt — sudo apt install jp2a
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ASCII, Art, Banners, Creative, Unicode, Text-Art, pyfiglet, figlet, cowsay, boxes]
    related_skills: [excalidraw]

---

# ASCII Art Skill

Multiple tools for different ASCII art needs. **Read the Decision Flow first**, then use the numbered tool docs for details.

## Decision Flow — read this first

Pick the first rule that fits the request:

| # | Request type | Tool | Status |
|---|---|---|---|
| 1 | **Render text as a big styled banner** | pyfiglet (local) → asciified API fallback | ✅ ready |
| 2 | **Put a message in a speech bubble with an animal/character** | cowsay | ⚙️ needs install |
| 3 | **Wrap text in a decorative frame/border** | boxes | ⚙️ needs install |
| 4 | **Draw art of a specific thing** (cat, rocket, feet…) | ascii.co.uk via curl | ✅ ready |
| 5 | **Convert a user-uploaded image to ASCII** | ascii-image-converter or jp2a | ⚙️ needs install |
| 6 | **Generate a QR code** | qrenco.de via curl | ✅ ready |
| 7 | **Show weather or moon phase** | wttr.in via curl | ✅ ready |
| 8 | **Something custom or creative** not covered above | LLM hand-drawn art | ✅ ready |

**⚠️ For items marked "needs install":** Do not silently fail. Tell the user which tool is missing and give them the install command. Then fall back to the next best option (e.g. LLM hand-drawn art for cowsay/boxes, Tool 4 for images if no file is provided).

**⚠️ toilet is intentionally omitted** from this flow — it outputs ANSI escape codes that render as garbage (`^[[31m…`) in Discord and other chat platforms. Only use toilet if the user is working in a terminal context and explicitly asks for colored art.

---

## Tool 1: Text Banners (pyfiglet — local, ✅ ready)

Render text as large ASCII art banners. 571 built-in fonts.

### Setup

```bash
pip install pyfiglet --break-system-packages -q
```

### Usage

```bash
python3 -m pyfiglet "YOUR TEXT" -f slant
python3 -m pyfiglet "TEXT" -f doom -w 80    # Set width
python3 -m pyfiglet --list_fonts             # List all 571 fonts
```

### Recommended fonts

| Style | Font | Best for |
|-------|------|----------|
| Clean & modern | `slant` | Project names, headers |
| Bold & blocky | `doom` | Titles, logos |
| Big & readable | `big` | Banners |
| Classic banner | `banner3` | Wide displays |
| Compact | `small` | Subtitles |
| Cyberpunk | `cyberlarge` | Tech themes |
| 3D effect | `3-d` | Splash screens |
| Gothic | `gothic` | Dramatic text |

### Tips

- Preview 2-3 fonts and let the user pick their favorite
- Short text (1-8 chars) works best with detailed fonts like `doom` or `block`
- Long text works better with compact fonts like `small` or `mini`

---

## Tool 2: Text Banners (asciified API — remote, ✅ ready, no install)

Free REST API that converts text to ASCII art. 250+ FIGlet fonts. Returns plain text directly — no parsing needed. Use this when pyfiglet is not installed or as a quick alternative.

### Usage (via terminal curl)

```bash
# Basic text banner (default font)
curl -s "https://asciified.thelicato.io/api/v2/ascii?text=Hello+World"

# With a specific font
curl -s "https://asciified.thelicato.io/api/v2/ascii?text=Hello&font=Slant"
curl -s "https://asciified.thelicato.io/api/v2/ascii?text=Hello&font=Doom"
curl -s "https://asciified.thelicato.io/api/v2/ascii?text=Hello&font=Star+Wars"
curl -s "https://asciified.thelicato.io/api/v2/ascii?text=Hello&font=3-D"
curl -s "https://asciified.thelicato.io/api/v2/ascii?text=Hello&font=Banner3"

# List all available fonts (returns JSON array)
curl -s "https://asciified.thelicato.io/api/v2/fonts"
```

### Tips

- URL-encode spaces as `+` in the text parameter
- The response is plain text ASCII art — no JSON wrapping, ready to display
- Font names are case-sensitive; use the fonts endpoint to get exact names
- Works from any terminal with curl — no Python or pip needed

---

## Tool 3: Cowsay (Message Art) ⚙️ needs install

Classic tool that wraps text in a speech bubble with an ASCII character.

### Setup

```bash
sudo apt install cowsay -y    # Debian/Ubuntu
# brew install cowsay         # macOS
```

**If not installed:** tell the user the install command, then fall back to LLM hand-drawn art (Tool 9) for the character, or just output the message as plain text.

### Usage

```bash
cowsay "Hello World"
cowsay -f tux "Linux rules"       # Tux the penguin
cowsay -f dragon "Rawr!"          # Dragon
cowsay -f stegosaurus "Roar!"     # Stegosaurus
cowthink "Hmm..."                  # Thought bubble
cowsay -l                          # List all characters
```

### Available characters (50+)

`beavis.zen`, `bong`, `bunny`, `cheese`, `daemon`, `default`, `dragon`,
`dragon-and-cow`, `elephant`, `eyes`, `flaming-skull`, `ghostbusters`,
`hellokitty`, `kiss`, `kitty`, `koala`, `luke-koala`, `mech-and-cow`,
`meow`, `moofasa`, `moose`, `ren`, `sheep`, `skeleton`, `small`,
`stegosaurus`, `stimpy`, `supermilker`, `surgery`, `three-eyes`,
`turkey`, `turtle`, `tux`, `udder`, `vader`, `vader-koala`, `www`

### Eye/tongue modifiers

```bash
cowsay -b "Borg"       # =_= eyes
cowsay -d "Dead"       # x_x eyes
cowsay -g "Greedy"     # $_$ eyes
cowsay -p "Paranoid"   # @_@ eyes
cowsay -s "Stoned"     # *_* eyes
cowsay -w "Wired"      # O_O eyes
cowsay -e "OO" "Msg"   # Custom eyes
cowsay -T "U " "Msg"   # Custom tongue
```

---

## Tool 4: Boxes (Decorative Borders) ⚙️ needs install

Draw decorative ASCII art borders/frames around any text. 70+ built-in designs.

### Setup

```bash
sudo apt install boxes -y    # Debian/Ubuntu
# brew install boxes         # macOS
```

**If not installed:** tell the user the install command, then fall back to a simple box drawn with `╔═╗ ║ ╚═╝` characters inline.

### Usage

```bash
echo "Hello World" | boxes                    # Default box
echo "Hello World" | boxes -d stone           # Stone border
echo "Hello World" | boxes -d parchment       # Parchment scroll
echo "Hello World" | boxes -d cat             # Cat border
echo "Hello World" | boxes -d dog             # Dog border
echo "Hello World" | boxes -d unicornsay      # Unicorn
echo "Hello World" | boxes -d diamonds        # Diamond pattern
echo "Hello World" | boxes -d c-cmt           # C-style comment
echo "Hello World" | boxes -d html-cmt        # HTML comment
echo "Hello World" | boxes -a c               # Center text
boxes -l                                       # List all 70+ designs
```

### Combine with pyfiglet or asciified

```bash
python3 -m pyfiglet "HERMES" -f slant | boxes -d stone
# Or without pyfiglet installed:
curl -s "https://asciified.thelicato.io/api/v2/ascii?text=HERMES&font=Slant" | boxes -d stone
```

---

## Tool 5: TOIlet (Colored Text Art) ⚙️ needs install — ⚠️ terminal-only

Like pyfiglet but with ANSI color effects. **Do not use for Discord or chat platforms** — ANSI escape codes render as raw garbage (`^[[31m…`) in non-terminal contexts. Only use this when the user is working in a terminal and explicitly requests colored art.

### Setup

```bash
sudo apt install toilet toilet-fonts -y    # Debian/Ubuntu
# brew install toilet                      # macOS
```

### Usage

```bash
toilet "Hello World"                    # Basic text art
toilet -f bigmono12 "Hello"            # Specific font
toilet --gay "Rainbow!"                 # Rainbow coloring
toilet --metal "Metal!"                 # Metallic effect
toilet -F border "Bordered"             # Add border
toilet -F border --gay "Fancy!"         # Combined effects
toilet -f pagga "Block"                 # Block-style font (unique to toilet)
toilet -F list                          # List available filters
```

### Filters

`crop`, `gay` (rainbow), `metal`, `flip`, `flop`, `180`, `left`, `right`, `border`

---

## Tool 6: Image to ASCII Art ⚙️ needs install

Convert images (PNG, JPEG, GIF, WEBP) to ASCII art. Only useful when the user has an actual image file to convert.

### Option A: ascii-image-converter (recommended, modern)

```bash
# Install
sudo snap install ascii-image-converter
# OR: go install github.com/TheZoraiz/ascii-image-converter@latest
```

```bash
ascii-image-converter image.png                  # Basic
ascii-image-converter image.png -C               # Color output
ascii-image-converter image.png -d 60,30         # Set dimensions
ascii-image-converter image.png -b               # Braille characters (pixel-accurate, terminal-only)
ascii-image-converter image.png -n               # Negative/inverted
ascii-image-converter https://url/image.jpg      # Direct URL
ascii-image-converter image.png --save-txt out   # Save as text
```

### Option B: jp2a (lightweight, JPEG only)

```bash
sudo apt install jp2a -y
jp2a --width=80 image.jpg
jp2a --colors image.jpg              # Colorized
```

**If not installed:** tell the user the install command. Do NOT attempt to hand-draw from the image — use Tool 4 (ascii.co.uk) to find pre-made art for the same subject instead.

---

## Tool 7: Search Pre-Made ASCII Art (ascii.co.uk — ✅ ready)

Search curated ASCII art from the web. Use `terminal` with `curl`.

### Source A: ascii.co.uk (recommended for pre-made art)

Large collection of classic ASCII art organized by subject. Art is inside HTML `<pre>` tags. Fetch the page with curl, then extract art with a small Python snippet.

**URL pattern:** `https://ascii.co.uk/art/{subject}`

**Step 1 — Fetch the page:**

```bash
curl -s 'https://ascii.co.uk/art/cat' -o /tmp/ascii_art.html
```

**Step 2 — Extract and rank art pieces:**

```python
import re, html
with open('/tmp/ascii_art.html') as f:
    text = f.read()
raw_blocks = re.findall(r'<pre[^>]*>(.*?)</pre>', text, re.DOTALL)
results = []
for raw in raw_blocks:
    clean = re.sub(r'<[^>]+>', '', raw)
    clean = html.unescape(clean)
    # split one big block into individual drawings (separated by 3+ blank lines)
    for chunk in re.split(r'\n{3,}', clean):
        chunk = chunk.strip()
        if len(chunk) < 50 or chunk.startswith('ASCII Character'):
            continue
        lines = [l for l in chunk.split('\n') if l.strip()]
        if len(lines) < 3:
            continue
        widths = [len(l) for l in lines]
        variance = max(widths) - min(widths)
        # FIGlet text banners are mostly alphanumeric; real art is mostly punctuation
        non_space = [c for c in chunk if c not in (' ', '\n')]
        alnum_ratio = sum(1 for c in non_space if c.isalnum()) / len(non_space) if non_space else 1
        if alnum_ratio > 0.5:
            continue  # skip FIGlet text banners
        # prefer compact pieces: 4-12 lines, 60-500 chars
        size_ok = (4 <= len(lines) <= 12) and (60 <= len(chunk) <= 500)
        score = (variance + 5) * (1.0 if size_ok else 0.15)
        results.append((score, chunk))
results.sort(reverse=True)
for _, art in results[:5]:   # show top 5 candidates
    print(art)
    print('\n---\n')
```

**Step 3 — Pick the best candidate.** Read all printed pieces and choose the one that best shows the subject's shape — prioritize pieces where you can immediately recognize what it is without reading any label. Compact pieces (5-10 lines) are usually more recognizable than complex multi-row art walls. If all 5 are abstract or unclear, fall back to Tool 9.

**Step 4 — If no output at all:** all pieces were FIGlet text banners. Fall back to Tool 9 (LLM hand-drawn art).

**Available subjects** (use as URL path):
- Animals: `cat`, `dog`, `horse`, `bird`, `fish`, `dragon`, `snake`, `rabbit`, `elephant`, `dolphin`, `butterfly`, `owl`, `wolf`, `bear`, `penguin`, `turtle`
- Objects: `car`, `ship`, `airplane`, `rocket`, `guitar`, `computer`, `coffee`, `beer`, `cake`, `house`, `castle`, `sword`, `crown`, `key`, `shoe`
- Body parts: `feet`, `hands`, `lips`, `eye`, `skull`
- Nature: `tree`, `flower`, `sun`, `moon`, `star`, `mountain`, `ocean`, `rainbow`
- Characters: `skull`, `robot`, `angel`, `wizard`, `pirate`, `ninja`, `alien`
- Holidays: `christmas`, `halloween`, `valentine`

**Tips:**
- Preserve artist signatures/initials — important etiquette
- Multiple art pieces per page — pick the best one for the user
- Works reliably via curl, no JavaScript needed
- **Try plural forms** for body parts: use `feet` not `foot`, `hands` not `hand` — plurals often have better art
- If the subject has no shape art (only FIGlet text banners), fall back to Tool 9

### Source B: GitHub Octocat API (fun easter egg)

Returns a random GitHub Octocat with a wise quote. No auth needed.

```bash
curl -s https://api.github.com/octocat
```

---

## Tool 8: Fun ASCII Utilities (via curl — ✅ ready)

These free services return ASCII art directly — great for fun extras.

### QR Codes as ASCII Art

```bash
curl -s "qrenco.de/Hello+World"
curl -s "qrenco.de/https://example.com"
```

### Weather as ASCII Art

```bash
curl -s "wttr.in/London"          # Full weather report with ASCII graphics
curl -s "wttr.in/Moon"            # Moon phase in ASCII art
curl -s "v2.wttr.in/London"       # Detailed version
```

---

## Tool 9: LLM-Generated Custom Art (Fallback — ✅ ready)

When tools above don't have what's needed, draw ASCII art by hand using line characters and the palette below.

### ⚠️ CRITICAL: Never use Braille characters (U+2800–U+28FF: ⠀⣿⣶⣤ etc.)

Braille block characters only make sense when a tool converts an image pixel-by-pixel (Tool 6). When drawn freehand by an LLM they produce unrecognizable solid blobs. **Always use traditional ASCII line characters instead.**

### Primary palette: line & shape characters

**Line drawing:** `/ \ | _ - ~ = ^ v ( ) [ ] { } < >`

**Curves & detail:** `, . ' " : ; ! * # @ + `

**Box drawing (for frames/borders only):** `╔ ╗ ╚ ╝ ║ ═ ╭ ╮ ╰ ╯ ┌ ┐ └ ┘ │ ─`

**Shading (use sparingly for fill/shadow):** `░ ▒ ▓ █ ▄ ▀ ▌ ▐`

**Symbols & accents:** `◆ ● ○ ★ ☆ ✦ ▲ ▼`

### How to draw shapes

Think of each line as a cross-section of the object viewed from the side or top. Use `/` `\` for diagonals, `_` for flat bottoms, `|` for vertical walls, `(` `)` for curves. Build the silhouette line by line.

**Example — a foot viewed from the side:**

```
   _____
  /     \___
 |          \___
  \____________/
    ||      ||
```

**Example — two feet from above (smelly feet scene):**

```
   ____        ____
  /    \      /    \
 | o  o |    | o  o |
 |      |    |      |
  \____/ \  / \____/
   |||||   \/   |||||
  ~stink~      ~stink~
```

### Rules

- Max width: 60 characters per line (terminal-safe)
- Max height: 25 lines for scenes
- Monospace only: every character takes equal width
- Make the subject recognizable from the silhouette alone — if you can't identify the shape without the label, redo it
