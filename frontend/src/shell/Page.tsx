/**
 * A screen's frame: the sticky page bar and the content region under it.
 *
 * ⚠️ **This exists to fix "the primary CTA is hidden below the fold", and it
 * fixes it structurally rather than by making a button bigger.** The bar is
 * sticky, so the one action a screen exists for is on screen at every scroll
 * position — and because `actions` is a single slot, a screen physically
 * cannot offer three equally-weighted primary buttons.
 *
 * ⚠️ **The header belongs to the SCREEN, not to the shell.** A context or a
 * portal would have let `App` own it, but then the title and the action would
 * live apart from the state they describe, and a screen rendered on its own in
 * a test would lose both. Here a screen is complete by itself.
 */

export function Page({
  title,
  subtitle,
  actions,
  status,
  children,
}: {
  title: string
  /** One line naming what this screen is for. U3: a page that does not say what it is for leaves the reader to infer it from the controls. */
  subtitle?: string
  /** The screen's single primary action, and at most one quiet action beside it. */
  actions?: React.ReactNode
  /** Live state — a run badge, a saved marker. Sits before the actions. */
  status?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <>
      <header className="topbar">
        <div className="topbar__titles">
          <h1 className="topbar__title">{title}</h1>
          {subtitle !== undefined && <p className="topbar__sub">{subtitle}</p>}
        </div>
        {(status !== undefined || actions !== undefined) && (
          <div className="topbar__actions">
            {status}
            {actions}
          </div>
        )}
      </header>

      <main id="main" className="content">
        {children}
      </main>
    </>
  )
}
