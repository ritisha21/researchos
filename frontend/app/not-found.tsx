import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center px-6">
      <p className="text-6xl font-bold gradient-text">404</p>
      <h2 className="text-xl font-semibold text-foreground">Page not found</h2>
      <p className="text-muted-foreground text-sm max-w-xs">
        The page you're looking for doesn't exist.
      </p>
      <Link href="/"
        className="px-4 py-2 rounded-xl bg-blue-500 hover:bg-blue-400 text-white text-sm font-medium transition-all">
        Go home
      </Link>
    </div>
  );
}
