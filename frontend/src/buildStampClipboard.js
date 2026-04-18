/**
 * Multi-line text copied when the user clicks the build stamp copy control.
 *
 * @param {string} buildCommit
 * @param {string} buildWhenEt formatted ET string
 * @param {string} serverWhenEt formatted ET string (or "—")
 */
export function formatBuildStampClipboard(buildCommit, buildWhenEt, serverWhenEt) {
  return [
    `Frontend ${buildCommit}`,
    `Build (ET): ${buildWhenEt}`,
    `Server Time (ET): ${serverWhenEt}`,
  ].join('\n')
}
