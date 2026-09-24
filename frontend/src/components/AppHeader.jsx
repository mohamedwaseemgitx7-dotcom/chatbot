import { forwardRef } from "react";
import { LogoMark, MenuIcon, NewChatIcon } from "./Icons";

const STATUS = {
  checking: { label: "Connecting…", tone: "muted" },
  online: { label: "Online", tone: "ok" },
  unreachable: { label: "Server unreachable", tone: "warn" },
  offline: { label: "Offline", tone: "warn" },
  demo: { label: "Demo mode", tone: "muted" },
};

const AppHeader = forwardRef(function AppHeader({ title, connection, drawer, drawerOpen, sidebarId, onMenu, onNewChat }, menuRef) {
  const status = STATUS[connection] || STATUS.checking;
  return (
    <header className="app-header">
      <div className="app-header__brand">
        {drawer && (
          <button
            ref={menuRef}
            type="button"
            className="icon-btn"
            onClick={onMenu}
            aria-label="Open conversations"
            aria-expanded={drawerOpen}
            aria-controls={sidebarId}
          >
            <MenuIcon />
          </button>
        )}
        <LogoMark size={30} />
        <span className="app-header__name">FarmerAssist</span>
      </div>

      <div className="app-header__chat">
        <div className="app-header__titles">
          <h1 className="app-header__title">{title}</h1>
          <p className={`status status--${status.tone}`} aria-live="polite">
            <span className="status__dot" aria-hidden="true" />
            {status.label}
          </p>
        </div>
        {drawer && (
          <button type="button" className="icon-btn" onClick={onNewChat} aria-label="New chat" title="New chat">
            <NewChatIcon />
          </button>
        )}
      </div>
    </header>
  );
});

export default AppHeader;
