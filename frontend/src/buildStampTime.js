/**
 * Format an ISO build timestamp for the footer: local calendar in pt-BR, clock in
 * America/New_York, with EST/EDT abbreviation (Intl picks the correct offset).
 *
 * @param {string} isoString
 * @returns {string}
 */
export function formatBuildDisplayTimeEastern(isoString) {
  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return isoString

  const dateTime = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/New_York',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)

  const tzParts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    timeZoneName: 'short',
  }).formatToParts(date)
  const abbr = tzParts.find(p => p.type === 'timeZoneName')?.value ?? 'ET'

  return `${dateTime} ${abbr}`
}
