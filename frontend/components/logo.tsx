import Link from "next/link";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link className="logo" href={compact ? "/dashboard" : "/"}>
      <span className="logo-mark" aria-hidden="true">
        G
      </span>
      <span>Growly</span>
    </Link>
  );
}
