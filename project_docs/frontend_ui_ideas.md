# Frontend UI Brainstorming & Ideas

This document serves as a living collection of the requested frontend UI improvements. Once all ideas are gathered, they will be converted into a formal Implementation Plan for approval.

## 1. Window Behavior (Launch)
- **Vertical Fullscreen**: When the app launches, utilize Electron's `screen` API to automatically calculate the monitor's work area height. The window will spawn with maximum vertical height from the top edge (`y: 0`), while maintaining a set width.

## 2. Top Menu / Header Reorganization
- **App Title & Status Indicator**: Relocate the backend `status-indicator` so it sits directly below the "Text-to-Ableton" application title on the left.
- **Settings Button**: Move the settings button to the far right edge of the top menu bar.
- **New Session Button**: Center the "NEW SESSION" button within the top bar, occupying the space between the title/status area and the settings button on the right.

## 3. Session Info & Cost Tracking
- **UI Overhaul**: Redesign the current "Session Info & Cost" section for much better readability, layout, and visual hierarchy.
- **New Metric (Cost per Prompt)**: Add a new metric tracking the cost of the *most recent* user prompt. This should be displayed at the top of the cost breakdown. *(Note: This will require backend logic to calculate and transmit per-prompt costs).*
- **Relocation**: Move the "Session Info & Cost" out of the Settings Modal and onto the main screen so it is easily accessible without cluttering the primary workspace. *(Pending placement decision based on proposed options)*

## 4. Future Features (Post-UI Overhaul)
- **Session Browser**: A major new feature to browse past sessions, preview their contents, and seamlessly open them to continue working or extract information. This will require new UI views and significant backend state-management updates to support saving, loading, and swapping session histories.
