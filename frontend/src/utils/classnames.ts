/**
 * Combine class names conditionally
 * Lightweight alternative to clsx
 */
export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}
