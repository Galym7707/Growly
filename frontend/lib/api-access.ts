/** The same public endpoint policy is used by middleware and the API proxy. */
export function isPublicGrowlyPath(path: string[], method: string): boolean {
  if (path.length !== 2 || !path[1]) return false;
  if (method === "POST") {
    return path[0] === "auth" && path[1] === "register";
  }
  return method === "GET" && ["share-links", "invitations"].includes(path[0]);
}

export function isPublicGrowlyRequest(pathname: string, method: string): boolean {
  const prefix = "/api/growly/";
  return (
    pathname.startsWith(prefix) &&
    isPublicGrowlyPath(pathname.slice(prefix.length).split("/"), method)
  );
}
