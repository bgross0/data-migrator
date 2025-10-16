import { useEffect, useRef, useState } from 'react'
import { createUniver, LocaleType, mergeLocales } from '@univerjs/presets'
import { UniverSheetsCorePreset } from '@univerjs/preset-sheets-core'
import UniverPresetSheetsCoreEnUS from '@univerjs/preset-sheets-core/locales/en-US'
import * as XLSX from 'xlsx'
import '@univerjs/preset-sheets-core/lib/index.css'

interface SpreadsheetPreviewProps {
  file: File
}

export default function SpreadsheetPreview({ file }: SpreadsheetPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const univerRef = useRef<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!containerRef.current || !file) return

    const initPreview = async () => {
      try {
        setLoading(true)
        setError(null)

        // Read file as array buffer
        const arrayBuffer = await file.arrayBuffer()

        // Check if it's a CSV file
        const isCsv = file.name.toLowerCase().endsWith('.csv')

        let workbookData: any

        if (isCsv) {
          // Convert CSV to XLSX workbook first
          const text = new TextDecoder().decode(arrayBuffer)
          const csvWorkbook = XLSX.read(text, { type: 'string' })

          // Convert to Univer format
          const firstSheet = csvWorkbook.Sheets[csvWorkbook.SheetNames[0]]
          const jsonData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 }) as any[][]

          // Create Univer-compatible workbook data
          workbookData = {
            sheets: {
              sheet1: {
                id: 'sheet1',
                name: csvWorkbook.SheetNames[0] || 'Sheet1',
                cellData: convertToUniverCellData(jsonData),
              }
            },
            sheetOrder: ['sheet1']
          }
        } else {
          // For Excel files, we'll use the Univer preset which handles Excel natively
          workbookData = null // Will use createWorkbook with file
        }

        // Initialize Univer
        const { univerAPI } = createUniver({
          locale: LocaleType.EN_US,
          locales: {
            [LocaleType.EN_US]: mergeLocales(
              UniverPresetSheetsCoreEnUS,
            ),
          },
          presets: [
            UniverSheetsCorePreset({
              container: containerRef.current!,
            }),
          ],
        })

        // Store reference for cleanup
        univerRef.current = univerAPI

        // Load the workbook
        if (workbookData) {
          // CSV: Use manually created workbook data
          univerAPI.createWorkbook(workbookData)
        } else {
          // Excel: Convert to Univer format using xlsx library
          try {
            const excelWorkbook = XLSX.read(arrayBuffer, { type: 'array' })
            const firstSheetName = excelWorkbook.SheetNames[0]
            const firstSheet = excelWorkbook.Sheets[firstSheetName]
            const jsonData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 }) as any[][]

            workbookData = {
              sheets: {
                sheet1: {
                  id: 'sheet1',
                  name: firstSheetName || 'Sheet1',
                  cellData: convertToUniverCellData(jsonData),
                }
              },
              sheetOrder: ['sheet1']
            }

            univerAPI.createWorkbook(workbookData)
          } catch (importError) {
            console.error('Failed to import XLSX:', importError)
            throw new Error('Failed to load Excel file. Please check the file format.')
          }
        }

        setLoading(false)
      } catch (err) {
        console.error('Failed to initialize preview:', err)
        setError(err instanceof Error ? err.message : 'Failed to load file preview')
        setLoading(false)
      }
    }

    initPreview()

    // Cleanup on unmount
    return () => {
      if (univerRef.current) {
        try {
          univerRef.current.dispose()
        } catch (e) {
          console.error('Error disposing Univer:', e)
        }
      }
    }
  }, [file])

  // Helper function to convert sheet data to Univer cell format
  const convertToUniverCellData = (data: any[][]) => {
    const cellData: any = {}

    data.forEach((row, rowIndex) => {
      if (!cellData[rowIndex]) {
        cellData[rowIndex] = {}
      }

      row.forEach((cell, colIndex) => {
        cellData[rowIndex][colIndex] = {
          v: cell === null || cell === undefined ? '' : String(cell),
        }
      })
    })

    return cellData
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Preview Error</h3>
            <p className="mt-1 text-sm text-red-700">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="relative">
      {loading && (
        <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10 rounded-lg">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-sm text-gray-600">Loading preview...</p>
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm font-medium text-gray-700">{file.name}</span>
              <span className="text-xs text-gray-500">
                ({(file.size / 1024).toFixed(1)} KB)
              </span>
            </div>
            <span className="text-xs text-gray-500">Read-only preview</span>
          </div>
        </div>

        <div
          ref={containerRef}
          style={{ height: '600px', width: '100%' }}
          className="univer-container"
        />
      </div>
    </div>
  )
}
