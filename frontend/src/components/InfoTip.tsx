interface Props {
  text: string
}

/** Keyboard- and screen-reader-accessible hover hint for metric definitions. */
export function InfoTip({ text }: Props) {
  return (
    <span className="info" tabIndex={0} role="img" aria-label={text} data-tip={text}>
      i
    </span>
  )
}
