/** Run links: ?run=<id> makes a run reloadable and shareable. Only run ids are accepted. */
const RUN_ID = /^[A-Za-z0-9][A-Za-z0-9-]{0,80}$/;

export function runIdFromSearch(search: string): string | null {
  const value = new URLSearchParams(search).get("run");
  return value && RUN_ID.test(value) ? value : null;
}

export function withRunParam(search: string, id: string | null): string {
  const params = new URLSearchParams(search);
  if (id) params.set("run", id);
  else params.delete("run");
  const s = params.toString();
  return s ? `?${s}` : "";
}
