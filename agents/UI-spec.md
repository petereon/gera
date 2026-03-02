# Frontend Specification: Gera UI

## 1. Design Philosophy & Metaphor

The core aesthetic is **"Minimalistic Floating Islands."**
The application is not a single flat surface. It consists of distinct, rounded panels ("islands") that float above a subtle background plane. Depth is conveyed through soft, layered shadows and significant negative space between containers. The UI must feel airy, light, and uncluttered.

## 2. Design Tokens (CSS Variables)

These tokens define the look and must be used consistently to achieve the floating effect.

### 2.1. Color Palette

Use a strictly limited palette to maintain minimalism.

```css
:root {
  /* Backgrounds */
  --app-bg: #F5F7FA; /* Very subtle light gray/off-white, NOT pure white */
  --surface-primary: #FFFFFF; /* The color of the "Islands" */
  --surface-secondary: #F0F2F5; /* Inputs, inactive pills, subtle backgrounds */

  /* Text */
  --text-primary: #1A1A1A; /* Main headings, body text */
  --text-secondary: #6B7280; /* Metadata, captions, inactive icons */
  --text-tertiary: #9CA3AF; /* Placeholders */

  /* Accent (Brand Color) */
  --accent-blue: #3B82F6; /* Primary buttons, active events */
  --accent-blue-subtle: #DBEAFE; /* Light backgrounds for active states */
}

```

### 2.2. Shape & Depth (Crucial)

The entire aesthetic relies on these two variables. Do not use harsh 1px borders to define space; use shadows.

```css
:root {
  /* Radii - Rounded corners are essential */
  --radius-xl: 24px; /* Main application panes ("Islands") */
  --radius-lg: 16px; /* Internal cards, large buttons, event blocks */
  --radius-md: 12px; /* Navigation pills, inputs */
  --radius-sm: 8px;  /* Small elements */

  /* Shadows - Layered shadows for soft, diffused depth */
  /* Shadow-sm: For interactive elements on hover */
  --shadow-sm: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  
  /* Shadow-md: The default state for the main "Islands" */
  --shadow-md: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
  
  /* Shadow-lg: For dragged items or modals */
  --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.02);
}

```

### 2.3. Typography

Use a clean, modern sans-serif (e.g., Inter, Roboto, system-ui).

## 3. Global Layout Architecture

The application uses a fixed 3-column CSS Grid layout with significant gaps.

* **Container:** Full viewport height (`100vh`), background color `var(--app-bg)`. Padding around the edges (e.g., `24px`).
* **Grid Structure:**
* Left Pane: Fixed width (~260px).
* Center Pane: Flexible width (`1fr`).
* Right Pane: Fixed width (~320px).


* **Gap:** Significant spacing between columns (e.g., `32px`).

## 4. Base Component: The "Island" Pane

All three main columns must use this base container style.

```css
.island-pane {
  background-color: var(--surface-primary);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  /* No borders. The shadow defines the edge. */
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px; /* Internal spacing between widgets */
}

```

## 5. Component Specifications

### 5.1. Left Pane Components

* **Navigation Pills (Inbox, Today, etc.):**
* Flex row layout.
* Container: `background: transparent`.
* Items: `border-radius: var(--radius-md)`, padding `8px 12px`.
* **Active State:** `background-color: var(--surface-secondary)` (or a very subtle tint of the accent brand color). Text color changes to primary.
* **Inactive State:** Transparent background. Text color secondary.


* **Floating Note Cards:**
* These are "mini-islands" nested inside the main island.
* Style: `background: var(--surface-primary)`, `border-radius: var(--radius-lg)`, `box-shadow: var(--shadow-sm)`. alternatively, use a subtle border `1px solid var(--surface-secondary)` if shadows feel too heavy nested.
* Layout: Flex column. Title (bold), Body truncated to 2 lines.
* **Interaction:** Must be draggable. On hover, translate Y up by 2px and increase shadow slightly.


* **Quick Capture Input:**
* Shape: Pill/Capsule (`border-radius: 999px`).
* Background: `var(--surface-secondary)`.
* No border.



### 5.2. Center Pane (Calendar Mode)

* **Calendar Grid:**
* Minimalist. Do not use heavy grid lines. Use extremely subtle borders (`1px solid var(--surface-secondary)`) just for the rows/columns, or even just dots at intersections.


* **Event Blocks:**
* Shape: `border-radius: var(--radius-lg)`.
* **Standard Event:** Background `var(--accent-blue)`. Text color white.
* **Ghost Event (Dragging state):** Background `var(--accent-blue)` with `opacity: 0.4`.
* Content spacing: Padding `12px`. Flex column layout. Small icon + Title.



### 5.3. Right Pane (Context Inspector)

* **Widgets (Linked Tasks, Details):**
* Distinct sections separated by whitespace or very subtle dividers.


* **Buttons (e.g., "Join Video Call"):**
* Full width, comfortable height (~48px).
* Shape: Capsule/Pill (`border-radius: 999px`).
* Style: Background `var(--accent-blue)`, text white, no border. Shadow-sm.



## 6. Interactions & States

* **Drag and Drop:**
* When dragging a card from the Left Pane, the original card should fade slightly.
* A "Ghost" image of the card follows the cursor.
* When hovering over a valid Calendar Drop Zone, show a "snapped" translucent blueprint of where the event will land (The "Ghost Event" style defined above).


* **Hover States:**
* Interactive elements (cards, buttons, actionable list items) must have a subtle "lift" effect on hover. Transition `transform` and `box-shadow` over `200ms ease`.