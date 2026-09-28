import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CommentaryPanel } from './CommentaryPanel'
import type { Commentary } from '../types'

const sample: Commentary = {
  text: 'Bullish confluence detected with rising momentum.',
  risk_note: 'Educational use only.',
  source: 'llm:gpt-4o-mini',
  generated_at: '2026-09-26T09:26:24Z',
}

describe('CommentaryPanel', () => {
  it('shows placeholder when no commentary yet', () => {
    render(<CommentaryPanel commentary={null} />)
    expect(screen.getByTestId('commentary-empty')).toBeInTheDocument()
  })

  it('renders text, risk note and source badge', () => {
    render(<CommentaryPanel commentary={sample} />)
    expect(screen.getByTestId('commentary-text')).toHaveTextContent('Bullish confluence')
    expect(screen.getByText(/Educational use only/)).toBeInTheDocument()
    expect(screen.getByTestId('commentary-source')).toHaveTextContent('llm:gpt-4o-mini')
  })
})
