/**
 * FR-1 — the person in charge loads and manages the department's data.
 *
 * The wiring only: `DatasetPanel` is the display and carries the reasoning
 * behind what it shows. Split the way `AdminScreen` is split from
 * `AccountsPanel`, so the report can be rendered and read back in a test
 * without a query client.
 *
 * ⚠️ **A refused import is a SUCCESS at this layer**, which is why the outcome
 * comes from `mutation.data` and not from `mutation.error`. The endpoint answers
 * 200 with `accepted: false` and the report; treating that as an error would
 * lose the report, which is the requirement's whole output.
 */

import { useState } from 'react'

import {
  useDataset,
  useImportDataset,
  useWithdrawDataset,
} from '@/api/queries'
import { DatasetPanel } from '@/features/dataset/DatasetPanel'

export function DatasetScreen() {
  const dataset = useDataset(true)
  const importing = useImportDataset()
  const withdrawing = useWithdrawDataset()
  const [chosen, setChosen] = useState<File[]>([])

  if (dataset.isError) {
    return (
      <section className="screen">
        <h2>Données du département</h2>
        <p className="empty">
          Seul le responsable des emplois du temps peut charger les données du
          département.
        </p>
      </section>
    )
  }

  const outcome = importing.data ?? withdrawing.data ?? null

  return (
    <DatasetPanel
      inForce={outcome?.dataset ?? dataset.data ?? null}
      outcome={outcome}
      chosen={chosen.length}
      importing={importing.isPending}
      withdrawing={withdrawing.isPending}
      failed={importing.isError || withdrawing.isError}
      onChoose={setChosen}
      onImport={() => {
        if (chosen.length === 0) return
        withdrawing.reset()
        importing.mutate(chosen, {
          onSuccess: (result) => {
            if (result.accepted) setChosen([])
          },
        })
      }}
      onWithdraw={() => {
        importing.reset()
        withdrawing.mutate()
      }}
    />
  )
}
