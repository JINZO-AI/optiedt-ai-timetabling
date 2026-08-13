import { useState } from 'react'

import {
  useAccounts,
  useCalendar,
  useCreateAccount,
  useCurrentUser,
  useDeleteAccount,
  useInstance,
  useResetCalendar,
  useSaveCalendar,
} from '@/api/queries'
import { userMessage } from '@/api/errors'
import { AccountsPanel } from '@/features/admin/AccountsPanel'
import { CalendarEditor } from '@/features/admin/CalendarEditor'
import { Page } from '@/shell/Page'

type Tab = 'calendar' | 'accounts'

const TAB_LABELS: Record<Tab, string> = {
  calendar: 'Academic calendar',
  accounts: 'Accounts',
}

/**
 * FR-9 and FR-11 — the administrator's two surfaces, on one screen.
 *
 * ⚠️ **One screen because SRS Table 2 gives them to one actor**: *"management
 * of the accounts and of the calendar"*. Splitting them into two nav entries
 * would suggest two rights where the specification states one.
 *
 * ⚠️ **What is hidden here is not what is forbidden.** `App.tsx` offers this
 * link to an administrator only, and every endpoint under it checks the role
 * for itself — a client that hides a control has not prevented the request.
 * This component nevertheless refuses to render for another role, so a bookmark
 * or a typed URL does not produce a page of failed requests with no
 * explanation.
 */
export function AdminScreen() {
  const me = useCurrentUser()
  const instance = useInstance()
  const [tab, setTab] = useState<Tab>('calendar')

  const isAdministrator = me.data?.role === 'ADMINISTRATOR'
  const calendar = useCalendar(isAdministrator)
  const accounts = useAccounts(isAdministrator)
  const saveCalendar = useSaveCalendar()
  const resetCalendar = useResetCalendar()
  const createAccount = useCreateAccount()
  const deleteAccount = useDeleteAccount()

  if (me.isLoading)
    return (
      <Page title="Administration">
        <p className="empty">Loading…</p>
      </Page>
    )

  if (!isAdministrator)
    return (
      <Page title="Administration">
        <p className="warning">
          Calendar and account administration belongs to the Administrator role. Your account does
          not hold it.
        </p>
      </Page>
    )

  return (
    <Page
      title="Administration"
      subtitle="The academic calendar and the accounts — the two things the institution sets"
    >
      <div className="tabs">
        {(Object.keys(TAB_LABELS) as Tab[]).map((key) => (
          <button
            key={key}
            className={`tab${tab === key ? ' tab--active' : ''}`}
            aria-current={tab === key ? 'page' : undefined}
            onClick={() => setTab(key)}
          >
            {TAB_LABELS[key]}
          </button>
        ))}
      </div>

      {tab === 'calendar' &&
        (calendar.isLoading ? (
          <p className="empty">Loading the calendar…</p>
        ) : calendar.data ? (
          <CalendarEditor
            calendar={calendar.data}
            saving={saveCalendar.isPending || resetCalendar.isPending}
            error={
              saveCalendar.isError
                ? userMessage(saveCalendar.error, 'save')
                : resetCalendar.isError
                  ? userMessage(resetCalendar.error, 'save')
                  : null
            }
            onSave={(payload) => saveCalendar.mutate(payload)}
            onReset={() => resetCalendar.mutate()}
          />
        ) : (
          <p className="error" role="alert">
            The calendar could not be loaded.
          </p>
        ))}

      {tab === 'accounts' &&
        (accounts.isLoading ? (
          <p className="empty">Loading accounts…</p>
        ) : accounts.data ? (
          <AccountsPanel
            accounts={accounts.data}
            teachers={instance.data?.teachers ?? []}
            groups={instance.data?.groups ?? []}
            creating={createAccount.isPending}
            error={
              createAccount.isError
                ? userMessage(createAccount.error, 'save')
                : deleteAccount.isError
                  ? userMessage(deleteAccount.error, 'save')
                  : null
            }
            currentUsername={me.data?.username}
            onCreate={(body) => createAccount.mutate(body)}
            onDelete={(username) => deleteAccount.mutate(username)}
          />
        ) : (
          <p className="error" role="alert">
            The accounts could not be loaded.
          </p>
        ))}
    </Page>
  )
}
