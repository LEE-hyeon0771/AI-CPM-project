import React from 'react'

interface Table {
  title: string
  headers: string[]
  rows: any[][]
}

interface Card {
  title: string
  value: string
  subtitle?: string
}

interface TablesProps {
  tables: Table[]
  cards: Card[]
}

const Tables: React.FC<TablesProps> = ({ tables, cards }) => {
  return (
    <div className="space-y-6">
      {/* Cards */}
      {cards && cards.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4">요약 정보</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cards.map((card, index) => (
              <div key={index} className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-600 mb-1">
                  {card.title}
                </div>
                <div className="text-xl font-bold text-gray-900 mb-1">
                  {card.value}
                </div>
                {card.subtitle && (
                  <div className="text-xs text-gray-500">
                    {card.subtitle}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tables */}
      {tables && tables.length > 0 && (
        <div className="space-y-6">
          {tables.map((table, index) => (
            <div key={index} className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold mb-4">{table.title}</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      {table.headers.map((header, headerIndex) => (
                        <th
                          key={headerIndex}
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {table.rows.map((row, rowIndex) => (
                      <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        {row.map((cell, cellIndex) => (
                          <td
                            key={cellIndex}
                            className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                          >
                            {typeof cell === 'number' ? cell.toLocaleString() : String(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Tables
