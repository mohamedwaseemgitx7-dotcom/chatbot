import { useCallback, useEffect, useRef, useState } from "react";
import AppHeader from "./components/AppHeader";
import ChatWindow from "./components/ChatWindow";
import AboutDialog from "./components/AboutDialog";
import ConfirmDialog from "./components/ConfirmDialog";
import Sidebar from "./components/Sidebar";
import { useAssistant } from "./hooks/useAssistant";
import { useCloudSync } from "./hooks/useCloudSync";
import { useConnection } from "./hooks/useConnection";
import { useConversations } from "./hooks/useConversations";
import { useMediaQuery } from "./hooks/useMediaQuery";
import "./App.css";

const SIDEBAR_ID = "conversation-sidebar";
const focusComposer = () => document.getElementById("message-input")?.focus();

export default function App({ user = null, onLogout = null }) {
  const store = useConversations();
  const { dispatch, conversations, active, pending } = store;
  const sync = useCloudSync(store);
  const assistant = useAssistant(store, sync);
  const connection = useConnection();

  // Below 900px the sidebar becomes a drawer (phones and portrait tablets).
  const drawer = useMediaQuery("(max-width: 899px)");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [deleteState, setDeleteState] = useState({ busy: false, error: null });
  const menuRef = useRef(null);
  const returnFocus = useRef(null); // "menu" | "composer" | null — where focus goes after the drawer closes

  const modalDrawer = drawer && drawerOpen;

  useEffect(() => { if (!drawer) setDrawerOpen(false); }, [drawer]);

  // Move focus only after the drawer has closed and the page is interactive again.
  useEffect(() => {
    if (drawerOpen || !returnFocus.current) return;
    if (returnFocus.current === "menu") menuRef.current?.focus();
    else focusComposer();
    returnFocus.current = null;
  }, [drawerOpen]);

  const closeDrawer = useCallback((focusTarget = "menu") => {
    returnFocus.current = focusTarget;
    setDrawerOpen(false);
  }, []);
  const closeDrawerToMenu = useCallback(() => closeDrawer("menu"), [closeDrawer]);

  const selectConversation = useCallback((id) => {
    dispatch({ type: "select", id });
    if (drawer) closeDrawer("composer");
  }, [dispatch, drawer, closeDrawer]);

  const newChat = useCallback(() => {
    dispatch({ type: "startNew" });
    if (drawer && drawerOpen) closeDrawer("composer");
    else focusComposer();
  }, [dispatch, drawer, drawerOpen, closeDrawer]);

  const askDelete = useCallback((conversation) => {
    setDeleteState({ busy: false, error: null });
    setToDelete(conversation);
  }, []);

  const confirmDelete = async () => {
    if (!toDelete) return;
    setDeleteState({ busy: true, error: null });
    try {
      await sync.deleteRemote(toDelete);
      dispatch({ type: "delete", id: toDelete.id });
      setToDelete(null);
      setDeleteState({ busy: false, error: null });
    } catch (error) {
      setDeleteState({ busy: false, error: error?.message || "Couldn't delete this conversation. Please try again." });
    }
  };

  return (
    <div className="app">
      <div className="app__header" inert={modalDrawer ? "" : undefined}>
        <AppHeader
          ref={menuRef}
          title={active?.title || "New chat"}
          connection={connection}
          drawer={drawer}
          drawerOpen={drawerOpen}
          sidebarId={SIDEBAR_ID}
          onMenu={() => setDrawerOpen(true)}
          onNewChat={newChat}
        />
      </div>

      <div className="app__body">
        <Sidebar
          id={SIDEBAR_ID}
          conversations={conversations}
          activeId={active?.id ?? null}
          onSelect={selectConversation}
          onNewChat={newChat}
          onDelete={askDelete}
          drawer={drawer}
          open={drawerOpen}
          onClose={closeDrawerToMenu}
          user={user}
          onLogout={onLogout}
          onAbout={() => { if (drawer) setDrawerOpen(false); setAboutOpen(true); }}
        />
        {drawer && <div className={`scrim${drawerOpen ? " scrim--visible" : ""}`} onClick={closeDrawerToMenu} aria-hidden="true" />}

        <main className="app__main" inert={modalDrawer ? "" : undefined}>
          <ChatWindow
            conversation={active}
            pending={pending}
            assistant={assistant}
            connection={connection}
            syncNotice={sync.notice}
            onDismissSyncNotice={sync.dismissNotice}
            onRetrySync={sync.status === "error" ? sync.retryConnect : null}
          />
        </main>
      </div>

      <AboutDialog open={aboutOpen} onClose={() => setAboutOpen(false)} />

      <ConfirmDialog
        open={toDelete !== null}
        title="Delete this conversation?"
        message={toDelete ? `“${toDelete.title}” and its photos will be deleted. This can't be undone.` : ""}
        confirmLabel="Delete"
        busy={deleteState.busy}
        error={deleteState.error}
        onConfirm={confirmDelete}
        onCancel={() => { if (!deleteState.busy) setToDelete(null); }}
      />
    </div>
  );
}
