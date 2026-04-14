function base64EncodeUtf8(str) {
  const bytes = new TextEncoder().encode(str)
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary)
}

export function isLatin1(str) {
  // HTTP Basic in browsers/server stacks is not reliably UTF-8 for credentials.
  // Keep UX explicit by rejecting non-Latin-1 characters (e.g. emojis).
  return Array.from(str).every(ch => ch.codePointAt(0) <= 0xff)
}

export function buildBasicAuthHeader(credentials) {
  return `Basic ${base64EncodeUtf8(`${credentials.username}:${credentials.password}`)}`
}

export function buildCycleFormData(form) {
  const body = new FormData()
  body.append('players_csv', form.playersCsv)
  body.append('tournaments_csv', form.tournamentsCsv)
  for (const file of form.binaryFiles) body.append('binary_files', file)
  body.append('first', form.first)
  body.append('count', form.count)
  return body
}

