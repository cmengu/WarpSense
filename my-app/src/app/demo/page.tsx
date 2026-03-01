'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

const DEFAULT_SESSION_A = 'sess_novice_aluminium_001_001';
const DEFAULT_SESSION_B = 'sess_expert_aluminium_001_001';

export default function DemoLandingPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace(`/demo/${DEFAULT_SESSION_A}/${DEFAULT_SESSION_B}`);
  }, [router]);
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#090c10',
        color: '#dce8f0',
      }}
    >
      <div>Redirecting to demo...</div>
    </div>
  );
}
