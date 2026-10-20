export function buildStatusChangePayload(status: string, note: string) {
  const trimmedNote = note.trim()
  return trimmedNote ? { status, note: trimmedNote } : { status }
}
