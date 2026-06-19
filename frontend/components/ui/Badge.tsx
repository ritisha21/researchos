import { cn } from '@/lib/utils';
const variants = {
  default: 'bg-secondary text-muted-foreground',
  blue: 'bg-blue-500/15 text-blue-400 border border-blue-500/20',
  violet: 'bg-violet-500/15 text-violet-400 border border-violet-500/20',
  emerald: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20',
  amber: 'bg-amber-500/15 text-amber-400 border border-amber-500/20',
  rose: 'bg-rose-500/15 text-rose-400 border border-rose-500/20',
};
export function Badge({ children, variant = 'default', className }: { children: React.ReactNode; variant?: keyof typeof variants; className?: string }) {
  return <span className={cn('inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium', variants[variant], className)}>{children}</span>;
}
