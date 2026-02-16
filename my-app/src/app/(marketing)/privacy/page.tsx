/**
 * Privacy Policy placeholder — coming soon.
 */
import Link from 'next/link';

export const metadata = {
  title: 'Privacy Policy — WeldVision',
  description: 'WeldVision privacy policy. Coming soon.',
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center">
      <div className="max-w-2xl mx-auto px-6 text-center">
        <h1 className="text-4xl font-bold mb-6">Privacy Policy</h1>
        <p className="text-xl text-gray-400 mb-8">
          Our privacy policy is in development. Please check back soon.
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
