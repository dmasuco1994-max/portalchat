import { cn } from "@/lib/utils";

interface BrandProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  variant?: "full" | "mark";
  /** If true, render in inverse colors for dark backgrounds. */
  inverse?: boolean;
}

/** Brand identity for the portal. The mark is a chat bubble + node graph hybrid:
 *  reads as "messaging" + "routing" — what the product does. */
export function Brand({
  className,
  size = "md",
  variant = "full",
  inverse = false,
}: BrandProps) {
  const dims =
    size === "sm" ? "h-7" : size === "lg" ? "h-12" : "h-9";

  return (
    <span className={cn("inline-flex items-center gap-2.5", dims, className)}>
      <BrandMark className={cn("h-full w-auto", inverse && "text-white")} />
      {variant === "full" && (
        <span
          className={cn(
            "font-semibold tracking-tight",
            size === "sm" ? "text-sm" : size === "lg" ? "text-xl" : "text-base",
            inverse ? "text-white" : "text-foreground"
          )}
        >
          Portal
          <span className={cn(inverse ? "text-white/70" : "text-primary")}>
            .chat
          </span>
        </span>
      )}
    </span>
  );
}

function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="brand-grad" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop stopColor="oklch(0.48 0.10 190)" />
          <stop offset="0.5" stopColor="oklch(0.55 0.13 175)" />
          <stop offset="1" stopColor="oklch(0.68 0.17 150)" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="10" fill="url(#brand-grad)" />
      <path
        d="M11 13.5C11 12.1193 12.1193 11 13.5 11H22.5C26.0899 11 29 13.9101 29 17.5C29 21.0899 26.0899 24 22.5 24H17.5L13.7 27.4C13.3819 27.6864 12.8819 27.4536 12.8819 27.0273V24H13.5C12.1193 24 11 22.8807 11 21.5V13.5Z"
        fill="white"
        fillOpacity="0.95"
      />
      <circle cx="16.5" cy="17.5" r="1.2" fill="oklch(0.48 0.10 190)" />
      <circle cx="20.5" cy="17.5" r="1.2" fill="oklch(0.48 0.10 190)" />
      <circle cx="24.5" cy="17.5" r="1.2" fill="oklch(0.48 0.10 190)" />
    </svg>
  );
}
