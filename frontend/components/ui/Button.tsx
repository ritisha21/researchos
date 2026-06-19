import { cn } from '@/lib/utils';
import { Spinner } from './Spinner';
const variants = {
  primary: 'bg-blue-500 hover:bg-blue-400 text-white shadow-lg shadow-blue-500/20',
  secondary: 'glass border border-border hover:border-blue-500/40 text-foreground',
  ghost: 'hover:bg-secondary text-muted-foreground hover:text-foreground',
  danger: 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20',
};
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants; loading?: boolean; icon?: React.ReactNode;
}
export function Button({ children, variant = 'primary', loading, icon, className, disabled, ...props }: ButtonProps) {
  return (
    <button {...props} disabled={disabled || loading}
      className={cn('inline-flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed', variants[variant], className)}>
      {loading ? <Spinner size="sm" /> : icon}
      {children}
    </button>
  );
}
