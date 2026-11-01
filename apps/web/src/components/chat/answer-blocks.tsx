"use client"

import { CheckIcon, CopyIcon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { Artifact, ArtifactAction, ArtifactActions, ArtifactContent, ArtifactHeader, ArtifactTitle } from "@/components/ai-elements/artifact"
import { CitationMarker } from "@/components/chat/citation-marker"
import { Figure } from "@/components/chat/figure"
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { blockText, tableTsv } from "@/lib/chat/blocks"
import type { Block, Cell, KeyDataBlock, TableBlock } from "@/lib/chat/types"
import { copyText } from "@/lib/clipboard"
import { cn } from "@/lib/utils"

function CopyBlock({ label, text, testId }: { label: string; text: string; testId: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    if (!(await copyText(text))) {
      toast(`No se pudo copiar: ${label.toLowerCase()}`)
      return
    }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }
  return (
    <ArtifactAction data-testid={testId} label={copied ? "Copiado" : label} onClick={copy}>
      {copied ? <CheckIcon /> : <CopyIcon />}
    </ArtifactAction>
  )
}

/** The value and, when the service cited it, its marker. */
function CellValue({ cell, className, wrap = true }: { cell: Cell; className?: string; wrap?: boolean }) {
  return (
    <span className={cn("inline-flex items-baseline gap-x-1", wrap ? "flex-wrap" : "flex-nowrap")}>
      <Figure cell={cell} className={className} />
      {cell.cite !== null && cell.cite !== undefined ? <CitationMarker number={cell.cite + 1} /> : null}
    </span>
  )
}

function KeyData({ block }: { block: KeyDataBlock }) {
  return (
    <Artifact aria-label={block.title} data-testid="key-data" role="group">
      <ArtifactHeader>
        <ArtifactTitle>{block.title}</ArtifactTitle>
        <ArtifactActions>
          <CopyBlock label="Copiar datos" testId="copy-key-data" text={blockText(block)} />
        </ArtifactActions>
      </ArtifactHeader>
      <ArtifactContent>
        <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
          {block.items.map((item) => (
            <div className="flex min-w-0 flex-col gap-1" data-field={item.field} key={item.field}>
              <dt className="text-xs text-muted-foreground first-letter:uppercase">{item.label}</dt>
              <dd className="m-0 min-w-0 text-sm break-words">
                <CellValue cell={item} className={item.kind === "amount" ? "text-base" : undefined} />
              </dd>
            </div>
          ))}
        </dl>
        {block.note ? <p className="mt-3 text-xs text-muted-foreground">{block.note}</p> : null}
      </ArtifactContent>
    </Artifact>
  )
}

const numeric = (kind: string) => kind === "amount" || kind === "percent"

function DataTable({ block, onAsk }: { block: TableBlock; onAsk: (question: string) => void }) {
  const columns = block.columns.length
  return (
    <Artifact aria-label={block.title ?? "Tabla"} data-testid="data-table" role="group">
      <ArtifactHeader>
        <ArtifactTitle>{block.title ?? "Facturas"}</ArtifactTitle>
        <ArtifactActions>
          <CopyBlock label="Copiar tabla" testId="copy-table" text={tableTsv(block)} />
        </ArtifactActions>
      </ArtifactHeader>
      <ArtifactContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              {block.columns.map((column) => (
                <TableHead className={cn("h-9 px-4 text-xs font-medium text-muted-foreground", numeric(column.kind) && "text-right")} key={column.key} scope="col">
                  <span className="inline-block first-letter:uppercase">{column.label}</span>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {block.rows.map((row) => (
              <TableRow key={row.doc_id}>
                {row.cells.map((cell, index) => {
                  const column = block.columns[index]
                  return (
                    <TableCell className={cn("px-4 py-2", column && numeric(column.kind) && "text-right")} key={column?.key ?? index}>
                      {index === 0 ? (
                        <button
                          aria-label={`Ver los datos de la factura ${cell.text ?? ""}`}
                          className="cursor-pointer rounded-sm font-mono text-[0.8125rem] tabular-nums underline-offset-4 outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50"
                          data-testid="row-ask"
                          onClick={() => onAsk(row.question)}
                          type="button"
                        >
                          {cell.text}
                        </button>
                      ) : null}
                      {index === 0 && cell.cite != null ? <CitationMarker number={cell.cite + 1} /> : null}
                      {index !== 0 ? (
                        <CellValue cell={cell} wrap={false} />
                      ) : null}
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
          </TableBody>
          {block.summary ? (
            <TableFooter>
              <TableRow>
                <TableCell className="px-4 py-2 font-medium" colSpan={Math.max(1, columns - 1)}>
                  {block.summary.label}
                </TableCell>
                <TableCell className="px-4 py-2 text-right" data-testid="table-summary">
                  <Figure cell={{ text: block.summary.text, kind: block.summary.kind }} />
                  {block.summary.refs.map((ref) => <CitationMarker key={ref} number={ref + 1} />)}
                </TableCell>
              </TableRow>
            </TableFooter>
          ) : null}
        </Table>
        {block.note ? <p className="border-t px-4 py-2 text-xs text-muted-foreground">{block.note}</p> : null}
      </ArtifactContent>
    </Artifact>
  )
}

export function AnswerBlocks({ blocks, onAsk }: { blocks: Block[]; onAsk: (question: string) => void }) {
  return (
    <div className="flex w-full min-w-0 flex-col gap-3" data-testid="answer-blocks">
      {blocks.map((block, index) =>
        block.type === "key_data" ? <KeyData block={block} key={index} /> : <DataTable block={block} key={index} onAsk={onAsk} />
      )}
    </div>
  )
}
