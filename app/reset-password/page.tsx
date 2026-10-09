import Link from 'next/link'

export default function ResetPasswordPage() {
  return (
    <main className="auth-shell">
      <div className="auth-panel">
        <div className="auth-brand">
          <span className="brand-mark">S</span>
          <span>Signalroom</span>
        </div>
        <h1>Set a new password</h1>
        <p>Choose a strong password for your workspace.</p>
        <form className="auth-form">
          <label>
            New password
            <input type="password" defaultValue="Password123!" />
          </label>
          <label>
            Confirm password
            <input type="password" defaultValue="Password123!" />
          </label>
          <button type="submit" className="button-primary auth-button">Update password</button>
        </form>
        <div className="auth-links">
          <Link href="/login">Return to login</Link>
        </div>
      </div>
    </main>
  )
}
