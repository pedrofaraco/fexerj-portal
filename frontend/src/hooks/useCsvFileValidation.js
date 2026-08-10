import { useEffect, useState } from 'react'

import { validatePlayersCsvFile, validateTournamentsCsvFile } from '../csvUploadValidation'

export default function useCsvFileValidation(playersCsv, tournamentsCsv, mode = 'legacy') {
  const [playersCsvErrors, setPlayersCsvErrors] = useState([])
  const [tournamentsCsvErrors, setTournamentsCsvErrors] = useState([])
  const [playersCsvStatus, setPlayersCsvStatus] = useState('idle') // idle | checking | done
  const [tournamentsCsvStatus, setTournamentsCsvStatus] = useState('idle')

  useEffect(() => {
    if (!playersCsv) {
      let cancelled = false
      queueMicrotask(() => {
        if (cancelled) return
        setPlayersCsvErrors([])
        setPlayersCsvStatus('idle')
      })
      return () => {
        cancelled = true
      }
    }

    let cancelled = false
    queueMicrotask(() => {
      if (cancelled) return
      setPlayersCsvStatus('checking')
      setPlayersCsvErrors([])
    })

    validatePlayersCsvFile(playersCsv, mode).then(errors => {
      if (cancelled) return
      setPlayersCsvErrors(errors)
      setPlayersCsvStatus('done')
    })

    return () => {
      cancelled = true
    }
  }, [playersCsv, mode])

  useEffect(() => {
    if (!tournamentsCsv) {
      let cancelled = false
      queueMicrotask(() => {
        if (cancelled) return
        setTournamentsCsvErrors([])
        setTournamentsCsvStatus('idle')
      })
      return () => {
        cancelled = true
      }
    }

    let cancelled = false
    queueMicrotask(() => {
      if (cancelled) return
      setTournamentsCsvStatus('checking')
      setTournamentsCsvErrors([])
    })

    validateTournamentsCsvFile(tournamentsCsv, mode).then(errors => {
      if (cancelled) return
      setTournamentsCsvErrors(errors)
      setTournamentsCsvStatus('done')
    })

    return () => {
      cancelled = true
    }
  }, [tournamentsCsv, mode])

  const csvFilesValid =
    (!playersCsv || (playersCsvStatus === 'done' && playersCsvErrors.length === 0)) &&
    (!tournamentsCsv || (tournamentsCsvStatus === 'done' && tournamentsCsvErrors.length === 0))

  const csvFilesChecking =
    (playersCsv && playersCsvStatus === 'checking') ||
    (tournamentsCsv && tournamentsCsvStatus === 'checking')

  return {
    playersCsvErrors,
    tournamentsCsvErrors,
    playersCsvStatus,
    tournamentsCsvStatus,
    csvFilesValid,
    csvFilesChecking,
  }
}
