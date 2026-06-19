import { cn } from '@/lib/utils';
export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('glass rounded-2xl border border-border p-6', className)}>{children}</div>;
}
