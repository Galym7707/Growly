export function isAuthRequired(
  nodeEnv = process.env.NODE_ENV,
  explicitAuthRequired = process.env.NEXT_PUBLIC_AUTH_REQUIRED,
): boolean {
  if (nodeEnv === "production") return true;
  return explicitAuthRequired === "true";
}

export function isLocalAuthBypassAllowed(
  nodeEnv = process.env.NODE_ENV,
  explicitAuthRequired = process.env.NEXT_PUBLIC_AUTH_REQUIRED,
): boolean {
  return !isAuthRequired(nodeEnv, explicitAuthRequired);
}
