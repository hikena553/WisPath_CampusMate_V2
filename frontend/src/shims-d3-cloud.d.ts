declare module 'd3-cloud' {
  export interface CloudWord {
    text: string
    value?: number
    size?: number
    x?: number
    y?: number
    [key: string]: unknown
  }

  interface CloudLayout {
    size(size: [number, number]): CloudLayout
    words(words: CloudWord[]): CloudLayout
    padding(padding: number): CloudLayout
    rotate(rotate: () => number): CloudLayout
    font(font: string): CloudLayout
    fontWeight(fontWeight: string | ((d: CloudWord) => string)): CloudLayout
    fontSize(fontSize: (d: CloudWord) => number): CloudLayout
    on(event: 'end', listener: (words: CloudWord[]) => void): CloudLayout
    start(): void
    stop(): void
  }

  export default function cloud(): CloudLayout
}