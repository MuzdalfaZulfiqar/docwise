import type { SVGProps } from "react";

const base = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true } as const;

export const IconSend = (p: SVGProps<SVGSVGElement>) => <svg {...base} {...p}><path d="M12 19V5M5 12l7-7 7 7" /></svg>;
export const IconClose = (p: SVGProps<SVGSVGElement>) => <svg {...base} {...p}><path d="M6 6l12 12M18 6L6 18" /></svg>;
export const IconMenu = (p: SVGProps<SVGSVGElement>) => <svg {...base} {...p}><path d="M4 7h16M4 12h16M4 17h16" /></svg>;
export const IconTrash = (p: SVGProps<SVGSVGElement>) => <svg {...base} {...p}><path d="M4 7h16M10 11v6M14 11v6M6 7l1 12h10l1-12M9 7V4h6v3" /></svg>;
export const IconPlus = (p: SVGProps<SVGSVGElement>) => <svg {...base} {...p}><path d="M12 5v14M5 12h14" /></svg>;
export const IconFile = (p: SVGProps<SVGSVGElement>) => <svg {...base} {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z M14 3v5h5" /></svg>;

export const LogoMark = () => (
  <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
    <rect x="3.5" y="2.5" width="19" height="21" rx="3.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
    <rect x="7" y="8" width="12" height="4" rx="1.5" style={{ fill: "var(--mark)" }} />
    <path d="M7 16h12M7 19.5h7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);
