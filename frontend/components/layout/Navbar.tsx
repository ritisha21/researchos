'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FlaskConical, Map, Search, Upload, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

const nav = [
  { href: '/roadmap', label: 'Navigator', icon: Map },
  { href: '/papers',  label: 'Papers',    icon: Search },
  { href: '/upload',  label: 'Upload',    icon: Upload },
  { href: '/chat',    label: 'Chat',      icon: MessageSquare },
];

export function Navbar() {
  const path = usePathname();
  return (
    <nav className="sticky top-0 z-50 h-16 glass border-b border-border px-6 flex items-center justify-between">
      <Link href="/" className="flex items-center gap-2.5 font-bold">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
          <FlaskConical className="w-4 h-4 text-white" />
        </div>
        <span className="gradient-text">ResearchOS</span>
      </Link>
      <div className="flex items-center gap-1">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href}
            className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
              path.startsWith(href) ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
            )}>
            <Icon className="w-4 h-4" />
            <span className="hidden sm:inline">{label}</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}
