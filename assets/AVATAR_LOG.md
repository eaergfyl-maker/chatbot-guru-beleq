# Avatar log (GenAI use record)

The assignment asks us to keep track of how the avatar was made.

## Why this design
- Name: **Guru Beleq**. "Guru" is Indonesian for teacher and "beleq" is Sasak for big, so the Big Teacher.
- Look: a friendly big drum (the Gendang Beleq) with a face, teacher's glasses, padded drumsticks (`pemantok`) and a traditional red batik headcloth (`sapuk`), to match both the topic and the teacher role.

## GenAI version
| Item | Value |
|---|---|
| Tool used | Google Gemini Image Generation (Imagen / Gemini image generator) |
| Date | 31 October 2026 |
| Initial prompt | Friendly cartoon avatar of a large traditional Sasak drum (Gendang Beleq) with a kind face, round teacher glasses and a red headcloth, flat colours, circular badge style, plain background |
| Refined prompt | A friendly cartoon avatar and mascot character designed as a traditional Indonesian Sasak drum (Gendang Beleq). The character is a large, stout cylindrical wooden drum with traditional decorative rope lacing zig-zagging along its rich mahogany wood body. The drum head features a warm, cheerful, kind smiling face with gentle eyes, rosy cheeks, and round vintage teacher spectacles perched on its face. On top of the drum sits an authentic red traditional Sasak male headcloth (sapuq) tied with traditional Sasak batik motif patterns and a distinctive folded peak. The character is posed warmly in a circular badge icon frame, flanked by two small wooden drumsticks with padded cloth mallets. Flat vector art style, clean bold outlines, warm earthy color palette with warm brown wood, cream parchment drum skin, crimson red sapuq, minimalist solid light cream background, circular emblem composition, professional app icon mascot illustration. |
| Changes after the first result | Refined prompt to specify the cylindrical rope-laced mahogany drum body, batik-patterned Sasak `sapuk` headcloth, and padded cloth mallets (`pemantok`); resized to 512x512 PNG. |
| Final file | `assets/avatar.png` |

## 3D companion version
| Item | Value |
|---|---|
| File | `assets/guru_3d.png` (591x640, transparent PNG, RGBA) |
| Style | 3D Pixar/clay-style studio render derived from the Guru Beleq design above: the same rope-laced mahogany Gendang Beleq body, cream drum-skin face, round tortoiseshell teacher glasses, red batik `sapuk` headcloth and two padded `pemantok` mallets, now with arms and legs |
| Added | 22 November 2026 |
| Used on | the arched companion stage on `/chat` (`web/index.html`), the hero arch and chat preview on `/` (`web/landing.html`), and the header brand mark; served at `/guru_3d.png` |
| Still used | `assets/avatar.png` stays as the favicon and at `/avatar.png` (the flat badge reads better at 16 px) |
| Live 3D version | `web/guru3d.js` rebuilds this design in Three.js on `/chat` (modelled and painted in code, no AI-generated model); this PNG is its fallback and the landing-page image |
| Animation | the PNG has no rig (the live 3D version on `/chat` does, see above). As a sprite, the reactions (idle float, listening lean, greeting bounce, teaching bob, celebrate jump, thinking tilt, comfort sway, 67 wiggle) are CSS keyframes on the whole sprite, plus a 3D perspective tilt that follows the pointer |
| Tool and prompt | not recorded in this repository; add the image tool, date and prompt here so the GenAI record is complete |
