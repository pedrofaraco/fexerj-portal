function base64EncodeUtf8(str) {
  const bytes = new TextEncoder().encode(str)
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary)
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

export function postMultipart(url, formData, credentials, { signal } = {}) {
  return fetch(url, {
    method: 'POST',
    headers: {
      Authorization: buildBasicAuthHeader(credentials),
    },
    body: formData,
    signal,
  })
}

