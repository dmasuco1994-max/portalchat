"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

interface ContactAvatarProps {
  name: string;
  pictureUrl?: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZE_CLASSES: Record<NonNullable<ContactAvatarProps["size"]>, string> = {
  sm: "size-9 text-xs",
  md: "size-11 text-sm",
  lg: "size-14 text-base",
};

function initialsFrom(label: string): string {
  return (
    label
      .split(/[\s@.]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((s) => s[0]?.toUpperCase())
      .join("") || "?"
  );
}

/** Avatar that prefers a remote profile picture URL when available, and falls
 *  back to initials on a brand-gradient circle.
 *
 *  WhatsApp signs picture URLs with a short-lived token — when it expires the
 *  image fails to load. We swap to the initials fallback on error via a flag. */
export function ContactAvatar({
  name,
  pictureUrl,
  size = "md",
  className,
}: ContactAvatarProps) {
  const [errored, setErrored] = React.useState(false);
  const showImage = pictureUrl && !errored;
  const initials = initialsFrom(name);

  return (
    <span
      className={cn(
        "relative flex shrink-0 items-center justify-center overflow-hidden rounded-full font-semibold text-white",
        showImage ? "bg-muted" : "bg-brand-gradient",
        SIZE_CLASSES[size],
        className
      )}
    >
      {showImage ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={pictureUrl}
          alt={name}
          className="size-full object-cover"
          onError={() => setErrored(true)}
          loading="lazy"
        />
      ) : (
        <span>{initials}</span>
      )}
    </span>
  );
}
