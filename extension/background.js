// Service worker: holds the latest generated feedback, enables the toolbar
// button while there is some, and routes paste requests to the frame holding
// the last focused text box.

const MENU_ID = "paste-feedback";

async function getFeedback() {
  const { feedback } = await chrome.storage.session.get("feedback");
  return feedback || "";
}

async function refreshAction() {
  const text = await getFeedback();
  chrome.contextMenus.update(MENU_ID, { enabled: Boolean(text) }, () => void chrome.runtime.lastError);
  if (text) {
    await chrome.action.enable();
    await chrome.action.setBadgeText({ text: "●" });
    await chrome.action.setBadgeBackgroundColor({ color: "#2e8b57" });
    await chrome.action.setTitle({ title: `Paste feedback (${text.length} chars)` });
  } else {
    await chrome.action.disable();
    await chrome.action.setBadgeText({ text: "" });
    await chrome.action.setTitle({ title: "Generate feedback first" });
  }
}

async function flashWarning(tabId, title) {
  await chrome.action.setBadgeText({ tabId, text: "!" });
  await chrome.action.setBadgeBackgroundColor({ tabId, color: "#c0392b" });
  await chrome.action.setTitle({ tabId, title });
  setTimeout(async () => {
    // Clearing the per-tab overrides falls back to the global state.
    await chrome.action.setBadgeText({ tabId, text: null }).catch(() => {});
    await chrome.action.setTitle({ tabId, title: null }).catch(() => {});
    await chrome.action.setBadgeBackgroundColor({ tabId, color: null }).catch(() => {});
  }, 2000);
}

/** Paste into the given frame, or the tab's last-focused frame. */
async function pasteInto(tabId, frameId) {
  const text = await getFeedback();
  if (!text) return;

  if (frameId === undefined) {
    const key = `focus_${tabId}`;
    const stored = await chrome.storage.session.get(key);
    frameId = stored[key];
  }
  if (frameId === undefined) {
    await flashWarning(tabId, "Click into a text box first");
    return;
  }

  try {
    const res = await chrome.tabs.sendMessage(tabId, { type: "paste", text }, { frameId });
    if (!res || !res.ok) await flashWarning(tabId, "Click into a text box first");
  } catch (_) {
    await flashWarning(tabId, "Can't paste on this page");
  }
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: MENU_ID,
    title: "Paste feedback",
    contexts: ["editable"],
    enabled: false,
  }, () => void chrome.runtime.lastError);
  refreshAction();
});

chrome.runtime.onStartup.addListener(refreshAction);

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === "feedback" && msg.text) {
    chrome.storage.session.set({ feedback: msg.text }).then(refreshAction);
  } else if (msg.type === "focus" && sender.tab) {
    chrome.storage.session.set({ [`focus_${sender.tab.id}`]: sender.frameId });
  }
});

chrome.action.onClicked.addListener((tab) => pasteInto(tab.id));

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === MENU_ID && tab) pasteInto(tab.id, info.frameId);
});

chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.session.remove(`focus_${tabId}`);
});
