# Text-to-Ableton: Custom Device Manual

Welcome to the **Dynamic Rack Management System**. 

Text-to-Ableton allows you to completely customize the instruments and effects that the AI has access to. Instead of relying on hardcoded lists, the AI learns its toolset directly from the `.adg` (Ableton Device Group) files you place in the designated factory folder. 

This guide explains how to add new synths, how to ensure the AI understands them perfectly, and how to manage your creative palette.

---

## 1. Adding a New AI Device

You can expose *any* Ableton native device, VST, or complex effects chain to the AI by wrapping it in an Instrument Rack or Audio Effect Rack.

### Step-by-Step
1. **Create the Rack:** In Ableton Live, load your desired instrument or effect (e.g., Xfer Serum, or a huge Drum Buss chain). Select the device(s) and press `Ctrl+G` (Windows) or `Cmd+G` (Mac) to group them into a Rack.
2. **Map the Macros:** Map the most important parameters you want the AI to control to the 16 Macro knobs on the Rack. *(Note: The AI currently only manipulates the top 16 Macros).*
3. **Save the Rack:** Click the "Save" (Floppy Disk) icon on the Rack. 
4. **Install the Device:** Locate the saved `.adg` file and place it into the Text-to-Ableton presets directory within your Ableton User Library:
   `[Your User Library Path]/Presets/Text-to-Ableton/`
   *(You can also simply drag and drop the `.adg` from Ableton's browser directly into this folder if you've added it to your sidebar Places).*
   
**That's it!** The next time the backend boots up, it will automatically scan this folder, read the file, and inform the AI that this new device is available.

---

## 2. The Golden Rule: Descriptive Knob Naming

The AI does not have eyes; it relies entirely on the semantic meaning of text to understand what a knob does. By default, Ableton labels un-renamed knobs as "Macro 1", "Macro 2", etc. If the AI only sees "Macro 1", it will have no idea what it controls and will likely ignore it.

To guarantee perfect AI execution, **you must rename the Macro knobs descriptively in Ableton** before saving the `.adg`.

> [!TIP]
> **Best Practices for Naming**
> - **Be Specific:** Use "Filter 1 Cutoff" instead of just "Cutoff".
> - **Avoid Heavy Abbreviations:** Use "Pitch Envelope Amount" instead of "Pe Amt". The AI understands human audio-engineering concepts best.
> - **No AI Instructions Needed:** You don't need to explain *how* a filter works. The AI already knows what "Filter Cutoff" does musically and will modulate it accordingly.

---

## 3. Power User Tip: Complex Dropdowns (Info Text)

Ableton's Macro knobs are continuous (0 to 127). If you map a dropdown menu (e.g., an Oscillator Waveform selector with Sine, Saw, Square, Noise) to a Macro, the AI will use its best judgment to guess which slice of the 0-127 dial corresponds to which waveform.

If you want **pixel-perfect, explicit control** over dropdowns or complex toggle switches, you can use Ableton's "Info Text" feature as an escape hatch to pass direct instructions to the AI.

1. In Ableton, Right-Click the specific Macro knob on your Rack.
2. Select **Edit Info Text**.
3. Type the explicit numeric mappings. For example:
   `0=Sine, 33=Saw, 66=Square, 127=Noise`
4. Save the `.adg`.

When the system unzips your `.adg` file, it will read your Info Text and secretly pass it to the AI Retriever. The AI will follow your instructions flawlessly.

---

## 4. Managing the AI's Palette

Sometimes, less is more. If you give the AI 50 different synthesizers, it might suffer from "analysis paralysis" or pick a synth that doesn't fit your current workflow.

- **To remove a device:** Simply delete or move the `.adg` file out of the `Presets/Text-to-Ableton/` folder.
- **To curate a session:** We highly recommend maintaining a lean folder of 5 to 10 Archetype racks that fit the specific genre you are producing. This keeps the AI focused, fast, and token-efficient.

*(Future Update: The upcoming Text-to-Ableton Desktop UI will feature a drag-and-drop "AI Palette" manager, allowing you to visually toggle these devices on and off without touching your file system.)*
