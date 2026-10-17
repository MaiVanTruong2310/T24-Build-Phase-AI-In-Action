/** A committed save remains successful even if the subsequent refresh fails. */
export async function saveAndRefresh<T>(
  save: () => Promise<T>,
  onSaved: (result: T) => void,
  refresh: () => Promise<unknown>,
): Promise<{ result: T; refreshed: boolean }> {
  const result = await save()
  onSaved(result)
  try {
    await refresh()
    return { result, refreshed: true }
  } catch {
    return { result, refreshed: false }
  }
}
