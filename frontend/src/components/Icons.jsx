/* 24px line icons. `currentColor` lets CSS set the colour; all are decorative (aria-hidden). */
const base = {
  width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
  strokeWidth: 1.9, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true, focusable: false,
};

export const MenuIcon = () => (<svg {...base}><path d="M4 7h16M4 12h16M4 17h16" /></svg>);
export const NewChatIcon = () => (
  <svg {...base}><path d="M20 12.5V17a2 2 0 0 1-2 2H9l-5 3V6a2 2 0 0 1 2-2h7" /><path d="M18 3v6M15 6h6" /></svg>
);
export const SearchIcon = () => (<svg {...base}><circle cx="11" cy="11" r="6.5" /><path d="m20 20-4.2-4.2" /></svg>);
export const CloseIcon = () => (<svg {...base}><path d="M6 6l12 12M18 6 6 18" /></svg>);
export const TrashIcon = () => (
  <svg {...base}><path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3" /></svg>
);
export const ImageIcon = () => (
  <svg {...base}><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="8.5" cy="9.5" r="1.8" /><path d="m21 16-5-5-9 9" /></svg>
);
export const MicIcon = () => (
  <svg {...base}><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" /></svg>
);
export const StopIcon = () => (<svg {...base} stroke="none" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>);
export const SendIcon = () => (
  <svg {...base}><path d="M5 12h13M12 5l7 7-7 7" /></svg>
);
export const ArrowDownIcon = () => (<svg {...base}><path d="M12 5v14M5 12l7 7 7-7" /></svg>);
export const RetryIcon = () => (<svg {...base}><path d="M4 12a8 8 0 1 0 2.4-5.7L4 8.5" /><path d="M4 4v4.5h4.5" /></svg>);
export const AlertIcon = () => (<svg {...base}><circle cx="12" cy="12" r="9" /><path d="M12 7.5v5.5M12 16.5h.01" /></svg>);
export const WarningIcon = () => (<svg {...base}><path d="M12 3 2 20h20L12 3Z" /><path d="M12 10v4.5M12 17.5h.01" /></svg>);
export const InfoIcon = () => (<svg {...base}><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></svg>);
export const WifiOffIcon = () => (
  <svg {...base}><path d="M3 3l18 18M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 5.2-2.8M19 13a10 10 0 0 0-2.3-1.7M2 9.5a15 15 0 0 1 4.6-2.9M22 9.5A15 15 0 0 0 11 5.1M12 20h.01" /></svg>
);
export const UploadIcon = () => (<svg {...base}><path d="M12 16V4M7 9l5-5 5 5M4 20h16" /></svg>);

/** FarmerAssist mark: a sprouting leaf inside a rounded field plot. */
export function LogoMark({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true" focusable="false">
      <rect width="40" height="40" rx="11" fill="var(--brand-700)" />
      <path
        d="M20 31V18m0 4.5c-5 0-8.5-3.4-8.5-8.5 5 0 8.5 3.4 8.5 8.5Zm0-2.2c0-5 3.4-8.3 8.5-8.3 0 5-3.4 8.3-8.5 8.3Z"
        stroke="var(--text-on-brand)" strokeWidth="2.3" fill="none" strokeLinecap="round" strokeLinejoin="round"
      />
      <path d="M12 31h16" stroke="var(--text-on-brand)" strokeWidth="2.3" strokeLinecap="round" opacity="0.55" />
    </svg>
  );
}
