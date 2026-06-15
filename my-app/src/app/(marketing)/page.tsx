/**
 * WarpSense landing — "Instrument" (V1) design system.
 *
 * One combined page for investors and shipyard customers. Content is real and
 * verbatim from the pitch deck; no traction/accuracy claims (pre-prototype).
 * Sections compose from components/marketing; content from lib/warpsense-content.
 */

import { Nav } from '@/components/marketing/Nav';
import { HeatSpine } from '@/components/marketing/HeatSpine';
import { InstrumentHUD } from '@/components/marketing/InstrumentHUD';
import {
  Hero,
  ProofStrip,
  Problem,
  Statement,
  HowItWorks,
  Demo,
  Market,
  Moat,
  Validation,
  Team,
  Raise,
  Contact,
  Footer,
} from '@/components/marketing/sections';

export default function LandingPage() {
  return (
    <div className="min-h-[100dvh] overflow-x-hidden bg-[var(--ws-ink)] font-[family-name:var(--font-barlow)] text-[var(--ws-fg)]">
      <Nav />
      <HeatSpine />
      <InstrumentHUD />
      <main>
        <Hero />
        <ProofStrip />
        <Problem />
        <Statement />
        <HowItWorks />
        <Demo />
        <Market />
        <Moat />
        <Validation />
        <Team />
        <Raise />
        <Contact />
      </main>
      <Footer />
    </div>
  );
}
