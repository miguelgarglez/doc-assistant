export function HighlightedFragment({
  fragment,
  quote,
}: {
  fragment: string
  quote: string
}) {
  if (!quote) {
    return <>{fragment}</>
  }

  const index = fragment.indexOf(quote)
  if (index < 0) {
    return <>{fragment}</>
  }

  return (
    <>
      {fragment.slice(0, index)}
      <mark>{quote}</mark>
      {fragment.slice(index + quote.length)}
    </>
  )
}
