import './TypewriterLoader.css'

export function TypewriterLoader({ size = 'sm', className = '' }: { size?: 'sm' | 'md' | 'lg'; className?: string }) {
  return (
    <span className={`typewriter-loader typewriter-loader--${size} ${className}`} aria-hidden="true">
      <span className="typewriter-loader__scale">
        <span className="p124-typewriter">
          <span className="slide"><i /></span>
          <span className="paper" />
          <span className="keyboard" />
        </span>
      </span>
    </span>
  )
}
