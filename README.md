# Macro for Moving Apple Notes to Any Text Document
This macro automates moving Apple Notes into another document (e.g., TextEdit).  
It can be customized to perform any macro by changing the steps in `_begin_macro_`.

---

## Setup

You must select **four points** where the macro will click.  

**How to select a point:**
1. Click the **`Select`** button for the target.
2. Move your mouse so the cursor is over the desired location.
3. Press **Enter** to save the coordinates.

**Points to select:**

| Target         | Description |
|----------------|-------------|
| **first_note** | The first note you want the macro to start on. The macro will continue down the list until it reaches the end or you press **Esc**. |
| **return_notes** | The top label in Notes (e.g., **Today** or **Pinned**) — this is double-clicked so the down arrow works correctly. |
| **bottom_notes** | The bottom empty space in a note to avoid selecting tables or bullet points when selecting all. |
| **text_edit** | The top of your text document, such that when clicked it will activate the cursor in the document on the bottom line (the image shows macOS TextEdit). |

---

**Example:**

![Demo Setup](instructionImages/Demo%20Setup.png)

---

## Changing the Output Format

**Current Behavior in `_begin_macro_`:**
```python
pyautogui.write('"""')
pyautogui.press('enter')
self.mac_cmd('v')  # Paste
pyautogui.press('enter')
pyautogui.write('"""')
pyautogui.press('enter')
```

**To Change This**
1. Open the method `_begin_macro_`
2. Look for the comment `# Change how it outputs to document`
3. Replace with your own `pyautogui` commands (e.g., format as JSON, plain text, etc.)
