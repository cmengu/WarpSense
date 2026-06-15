/**
 * WarpSense marketing content — single source of truth for the landing page.
 *
 * Content is real and sourced from the WarpSense pitch deck (quotes, figures,
 * founder bios are verbatim). Honesty constraints applied per direction:
 *   - No traction / pilot-cycle claims.
 *   - No accuracy or performance numbers (no prototype/data yet).
 *   - How-It-Works describes the product *design*, not a deployed product.
 *
 * Swap CONTACT_EMAIL before launch — it is a placeholder.
 */

/** Founder contact. Swap if a dedicated team alias is set up before launch. */
export const CONTACT_EMAIL = 'chen_meng@u.nus.edu';

export const BRAND = {
  name: 'WarpSense',
  tagline: 'AI-Powered Weld Intelligence',
  oneLiner:
    'A clip-on sensor that monitors five structural parameters in real time during the weld — before any inspector walks over.',
} as const;

export const NAV_LINKS = [
  { href: '#problem', label: 'Problem' },
  { href: '#system', label: 'System' },
  { href: '#market', label: 'Market' },
  { href: '#validation', label: 'Validation' },
  { href: '#team', label: 'Team' },
] as const;

/**
 * Navigable sections, in scroll order, for the instrument HUD readout
 * (`02 / 10 · PROBLEM`). Connective bands (proof strip, statement) are
 * intentionally excluded — these are the destinations, not the seams.
 */
export const HUD_SECTIONS = [
  { id: 'top', label: 'Intro' },
  { id: 'problem', label: 'Problem' },
  { id: 'system', label: 'System' },
  { id: 'demo', label: 'Demo' },
  { id: 'market', label: 'Market' },
  { id: 'moat', label: 'Moat' },
  { id: 'validation', label: 'Validation' },
  { id: 'team', label: 'Team' },
  { id: 'raise', label: 'Raise' },
  { id: 'contact', label: 'Contact' },
] as const;

/**
 * Live product surfaces reachable from the landing footer. Internal/dev routes
 * (admin thresholds, dev tooling) and ID-dependent routes (replay, panel passes,
 * welder reports) are intentionally excluded — they are not public entry points.
 */
export const EXPLORE_LINKS = [
  { href: '/dashboard', label: 'Quality Dashboard' },
  { href: '/analysis', label: 'Analysis Engine' },
  { href: '/ai', label: 'On-Device AI' },
  { href: '/defects', label: 'Defect Library' },
  { href: '/simulator', label: 'Weld Simulator' },
  { href: '/compare', label: 'Compare Sessions' },
  { href: '/demo', label: 'Session Demos' },
] as const;

/** Honest credibility strip — replaces the original's fabricated logo wall. */
export const PROOF = [
  { value: '3', label: 'Active production shipyards' },
  { value: '4', label: 'Named industry leaders interviewed' },
  { value: '41 yrs', label: 'Deepest floor experience consulted' },
  { value: '5', label: 'Structural parameters measured' },
] as const;

export const HERO = {
  kicker: 'AI-Powered Weld Intelligence',
  // `emphasis` is rendered in the accent color inside the headline.
  headline: ['Weld defects caught before the', 'inspector', 'arrives'],
  emphasisIndex: 1,
  sub: 'WarpSense is a clip-on sensor system that monitors five structural parameters in real time during the weld. A pass-or-flag verdict is delivered the moment the joint is finished.',
  primaryCta: { label: 'See how it works', href: '#system' },
  secondaryCta: { label: 'Contact us', href: '#contact' },
} as const;

export const PROBLEMS = [
  {
    index: '01',
    label: 'No data during the weld',
    title: 'Inspection happens after the metal has cooled',
    body: "Today's quality control method: a trained inspector crawls into a ship's hull after the weld has cooled, camera in hand, and decides with their eyes. Zero data is captured between arc strike and inspection. By the time a defect is found, it's already inside finished metalwork.",
  },
  {
    index: '02',
    label: 'The expertise is retiring',
    title: 'The expert workforce is disappearing',
    body: "Reliable self-correction required welders with over a decade of intuition. That generation is retiring. Yards are filling roles with junior welders who haven't developed that judgment. The old system assumed expertise that no longer exists at scale.",
  },
] as const;

export const STEPS = [
  {
    index: '01',
    title: 'Clip on',
    body: 'WarpSense attaches to any welding tool. No hardware swap, no process change.',
  },
  {
    index: '02',
    title: 'Measure in real time',
    body: 'Five structural parameters captured continuously while the weld is being made.',
  },
  {
    index: '03',
    title: 'Instant verdict',
    body: 'A pass-or-flag result the moment the joint is finished — before any inspector is needed.',
  },
  {
    index: '04',
    title: 'See what X-ray misses',
    body: 'Targets internal cracks between metal layers — invisible to the naked eye and frequently missed even by X-ray.',
  },
] as const;

export const MARKET = {
  tiers: [
    {
      tier: 'TAM',
      value: '$4.7–7.8B',
      desc: 'Global welding inspection services — 3–5% of the US$156B shipbuilding market, growing at 4.5% CAGR.',
    },
    {
      tier: 'SAM',
      value: '$500M',
      desc: 'Quality-related spend and failure cost in Southeast Asia — the fastest-growing NDT sub-region at 11% CAGR.',
    },
    {
      tier: 'SOM',
      value: 'S$17–22M',
      desc: '12–15 yards across Singapore, Malaysia, and Indonesia.',
    },
  ],
  stages: [
    {
      index: 'Stage 1',
      title: 'Beachhead',
      body: '12–15 yards across Singapore, Malaysia & Indonesia · SGD 17–22M ARR.',
    },
    {
      index: 'Stage 2',
      title: 'Certification bodies',
      body: 'DNV and Bureau Veritas adoption triggers global portfolio roll-out.',
    },
    {
      index: 'Stage 3',
      title: 'Adjacent industries',
      body: 'Oil platforms, pressure vessels, and industrial fabrication.',
    },
  ],
} as const;

export const MOAT = [
  {
    index: '01',
    title: 'Hardware-agnostic by design',
    body: "Equipment manufacturers can't build this without undermining their own products. We can.",
  },
  {
    index: '02',
    title: 'Camera systems are blind',
    body: 'Optical inspection misses sub-surface defects by design. WarpSense measures what cameras cannot see.',
  },
  {
    index: '03',
    title: 'A dataset moat',
    body: 'The proprietary dataset required — real weld measurements matched to real inspection outcomes — does not exist anywhere. It can only be built through live deployment. Every weld session adds to an advantage no late entrant can purchase.',
  },
] as const;

export const VALIDATION = {
  intro:
    'Three active production shipyards. Four named industry leaders across operations, inspection, project management, and commercial functions. Every conversation in person, on the floor.',
  quotes: [
    {
      quote:
        'It takes more than ten years for a welder to develop the judgment to know what is acceptable by eye alone.',
      name: 'Mr Tuck Wai',
      role: 'Head of Digitalisation, PaxOcean · 41 years in marine industry',
    },
    {
      quote:
        'The current quality control method: eyes and a camera for documentation.',
      name: 'Mr Lee',
      role: 'Certified Surveyor & Internal Inspector, PaxOcean',
    },
    {
      quote:
        'The highest-cost defect source is heat buildup between weld passes — invisible until the X-ray, and directly measurable in real time.',
      name: 'Mr Sam',
      role: 'Project Manager, LITA Ocean',
    },
  ],
} as const;

export const TEAM = [
  {
    name: 'Ng Chen Meng',
    affiliation: 'Business & AI Systems · NUS',
    bio: 'Owns customer relationships and the AI verdict engine. Personally initiated and manages three active shipyard relationships.',
  },
  {
    name: 'Zhuzhen',
    affiliation: 'Computer Science · NUS',
    bio: 'Built the quality dashboard: raw sensor data to quality verdict. Owns the full stack from data pipeline to inspector alerts.',
  },
  {
    name: 'Yuan Yi Ning',
    affiliation: 'Computer Science · NTU',
    bio: 'Led every customer interview in person. The validation here carries real names and real quotes because she was physically in every conversation.',
  },
  {
    name: 'Sidhaarth Satish',
    affiliation: 'Integrated Design & Engineering · NUS',
    bio: 'Building the ruggedised sensor device from scratch — five simultaneous parameters, designed to survive arc flash, heat, and confined spaces.',
  },
] as const;

export const RAISE = {
  // Framed as the plan — forward-looking, not achieved.
  amount: 'SGD 150,000',
  allocation: [
    { label: 'Hardware', pct: 36.67 },
    { label: 'Software', pct: 23.33 },
    { label: 'Deployment', pct: 20 },
    { label: 'Operations & Legal', pct: 13.33 },
    { label: 'Contingency', pct: 6.67 },
  ],
  milestones: [
    {
      window: 'Months 1–6',
      points: [
        '3 sensors deployed across 3 live yards',
        'First 1,000 real welds recorded',
        'IP filing submitted',
        'A*STAR research partnership initiated',
      ],
    },
    {
      window: 'Months 7–12',
      points: [
        'First paying contract live',
        'SGD 1,500 / station / month (80 stations ≈ SGD 1.44M ARR per yard)',
        'Certification-body conversation opened',
        'Series A materials ready',
      ],
    },
  ],
} as const;

export const CONTACT = {
  headline: 'Talk to us',
  sub: 'Whether you operate a yard, work in inspection, or are looking at the space — we want to hear from you.',
} as const;
