# Feedback Generator: Paste (personal browser extension)

A Chrome/Edge/Brave extension that pastes the feedback you just generated
into whatever text box you're working in on another site. For personal use
only: it is loaded unpacked and never published.

## Install
1. Open `chrome://extensions` and turn on **Developer mode**.
2. Click **Load unpacked** and choose this `extension/` folder.
3. Optional: pin the extension to the toolbar.

After editing any file here, click the reload icon on the extension's card.

## Use
1. Generate feedback in the app (`http://localhost:5010`). The toolbar button
   turns on with a green dot.
2. On the other site, click into the comment box where the feedback should go.
3. Click the toolbar button, press **Alt+Shift+F**, or right-click the box and
   choose **Paste feedback**.

A red **!** on the button means no text box was selected (or the page blocks
extensions, like `chrome://` pages). The feedback stays available until you
generate new feedback or close the browser.

## Different app address
The app is matched at `http://localhost:5010` and `http://127.0.0.1:5010`.
If you run it elsewhere, edit the first `matches` entry in `manifest.json`
and reload the extension.

Change the keyboard shortcut at `chrome://extensions/shortcuts`.
