/** Run links: ?run=<id> makes a run reloadable and shareable. Only run ids are accepted. */
const RUN_ID = /^[A-Za-z0-9][A-Za-z0-9-]{0,80}$/;

export function runIdFromSearch(search: string): string | null {
  const value = new URLSearchParams(search).get("run");
  return value && RUN_ID.test(value) ? value : null;
}

/** /runs/<id>: the path form of a run link (the server serves the workbench for it). */
export function runIdFromPath(pathname: string): string | null {
  const m = /^\/runs\/([^/]+)\/?$/.exec(pathname);
  if (!m) return null;
  let id = m[1];
  try {
    id = decodeURIComponent(id);
  } catch {
    return null;
  }
  return RUN_ID.test(id) ? id : null;
}

export function runIdFromLocation(pathname: string, search: string): string | null {
  return runIdFromSearch(search) ?? runIdFromPath(pathname);
}

export function withRunParam(search: string, id: string | null): string {
  const params = new URLSearchParams(search);
  if (id) params.set("run", id);
  else params.delete("run");
  const s = params.toString();
  return s ? `?${s}` : "";
}
