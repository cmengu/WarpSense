/**
 * Terms of Service placeholder — coming soon.
 */
import Link from 'next/link';

export const metadata = {
  title: 'Terms of Service — WeldVision',
  description: 'WeldVision terms of service. Coming soon.',
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center">
      <div className="max-w-2xl mx-auto px-6 text-center">
        <h1 className="text-4xl font-bold mb-6">Terms of Service</h1>
        <p className="text-xl text-gray-400 mb-8">
          Our terms of service are in development. Please check back soon.
        </p>
        <Link
          href="/"
          className="text-blue-400 hover:text-blue-300 transition-colors"
        >
          ← Return to home
        </Link>
      </div>
    </div>
  );
}
