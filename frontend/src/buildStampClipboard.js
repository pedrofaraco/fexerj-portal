/**
 * Single line copied when the user clicks the build stamp copy control.
 *
 * @param {string} frontendSnapshot — short id of the `frontend/` tree (parity across envs)
 * @param {string} buildCommit — branch tip; can differ when snapshot matches
 */
export function formatBuildStampClipboard(frontendSnapshot, buildCommit) {
  return `Frontend ${frontendSnapshot} · commit ${buildCommit}`
}
