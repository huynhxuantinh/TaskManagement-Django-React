import type { ReactNode } from 'react'

export interface TableColumn<T> {
  key: string
  label: string
  render: (row: T) => ReactNode
}

export function DataTable<T>({ rows, columns, rowKey }: { rows: T[]; columns: TableColumn<T>[]; rowKey: (row: T) => string | number }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
      <table className="min-w-full border-collapse text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
          <tr>{columns.map((column) => <th key={column.key} className="px-5 py-3 font-bold">{column.label}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={rowKey(row)}>{columns.map((column) => <td key={column.key} className="px-5 py-4">{column.render(row)}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

