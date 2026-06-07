> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# OHLC by Pair Address

> Gets the candlesticks for a specific pair address

export const EndpointMeta = ({premium, cus, cusUnit, mainnetOnly}) => {
  const items = [];
  const planName = typeof premium === "string" ? premium : "Pro";
  if (premium) {
    items.push({
      icon: "\u26a0\ufe0f",
      label: "Premium endpoint",
      text: <>
          Requires the <strong>{planName} plan</strong> or above.{" "}
          <a href="/data-api/introduction/resources/premium-endpoints">
            View all
          </a>
          .
        </>
    });
  }
  if (cus) {
    const isDynamic = !!cusUnit;
    items.push({
      icon: "\u26a1",
      label: isDynamic ? "Dynamic cost" : "Endpoint cost",
      text: isDynamic ? <>
          {cus} CUs per {cusUnit}.{" "}
          <a href="/get-started/pricing#dynamic-endpoints">Learn more</a>.
        </> : <>
          {cus} CUs.{" "}
          <a href="/get-started/pricing">Learn more</a>.
        </>
    });
  }
  if (mainnetOnly) {
    items.push({
      icon: "\ud83d\udd17",
      label: "Mainnet only",
      text: <>Testnet chains are not supported.</>
    });
  }
  if (items.length === 0) return null;
  return <div className="endpoint-meta" style={{
    border: "1px solid var(--border-color, #e2e8f0)",
    borderRadius: "8px",
    overflow: "hidden",
    marginBottom: "16px",
    fontSize: "14px",
    lineHeight: "1.6",
    maxWidth: "100%"
  }}>
      <style dangerouslySetInnerHTML={{
    __html: `
            .endpoint-meta {
              --border-color: #e2e8f0;
              --row-bg: #f8fafc;
              --label-color: #0f172a;
              --text-color: #1f2937;
            }
            .endpoint-meta a {
              color: #0f7fff !important;
              text-decoration: underline;
            }
            @media (prefers-color-scheme: dark) {
              .endpoint-meta {
                --border-color: #374151 !important;
                --row-bg: #1e293b !important;
                --label-color: #f9fafb !important;
                --text-color: #e5e7eb !important;
              }
              .endpoint-meta a {
                color: #60a5fa !important;
              }
            }
            html.dark .endpoint-meta,
            [data-theme="dark"] .endpoint-meta {
              --border-color: #374151 !important;
              --row-bg: #1e293b !important;
              --label-color: #f9fafb !important;
              --text-color: #e5e7eb !important;
            }
            html.dark .endpoint-meta a,
            [data-theme="dark"] .endpoint-meta a {
              color: #60a5fa !important;
            }
          `
  }} />
      {items.map((item, i) => <div key={i} style={{
    display: "flex",
    alignItems: "baseline",
    gap: "8px",
    padding: "10px 14px",
    borderBottom: i < items.length - 1 ? "1px solid var(--border-color, #e2e8f0)" : "none",
    backgroundColor: "var(--row-bg, #f8fafc)"
  }}>
          <span style={{
    flexShrink: 0
  }}>{item.icon}</span>
          <span style={{
    wordBreak: "break-word",
    color: "var(--text-color, #1f2937)"
  }}>
            <strong style={{
    color: "var(--label-color, #0f172a)"
  }}>
              {item.label}:
            </strong>{" "}
            {item.text}
          </span>
        </div>)}
    </div>;
};

<EndpointMeta cus={150} />


## OpenAPI

````yaml /openapi-files/data-api/solana-api.json GET /token/{network}/pairs/{address}/ohlcv
openapi: 3.0.0
info:
  title: Moralis Solana API
  version: '1.0'
servers:
  - url: https://solana-gateway.moralis.io
security: []
paths:
  /token/{network}/pairs/{address}/ohlcv:
    get:
      tags:
        - Token
      summary: Get candlesticks for a pair address
      description: Gets the candlesticks for a specific pair address
      operationId: getCandleSticks
      parameters:
        - name: network
          required: true
          in: path
          description: The network to query
          schema:
            enum:
              - mainnet
              - devnet
            type: string
        - name: address
          required: true
          in: path
          description: The address to query
          schema:
            type: string
            example: So11111111111111111111111111111111111111112
        - name: cursor
          required: false
          in: query
          description: The cursor to the next page
          schema:
            type: string
        - name: fromDate
          required: true
          in: query
          description: >-
            The starting date (format in seconds or datestring accepted by
            momentjs)
          schema:
            default: '2024-10-09'
            type: string
        - name: toDate
          required: true
          in: query
          description: >-
            The ending date (format in seconds or datestring accepted by
            momentjs)
          schema:
            default: '2024-10-10'
            type: string
        - name: timeframe
          required: true
          in: query
          description: The interval of the candle stick
          schema:
            default: 1min
            enum:
              - 1s
              - 10s
              - 30s
              - 1min
              - 5min
              - 10min
              - 30min
              - 1h
              - 4h
              - 12h
              - 1d
              - 1w
              - 1M
            type: string
        - name: currency
          required: true
          in: query
          description: The currency format
          schema:
            default: usd
            enum:
              - usd
              - native
            type: string
        - name: limit
          required: false
          in: query
          description: The limit per page
          schema:
            minimum: 1
            maximum: 1000
            default: 100
            type: number
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GetCandleSticksResponse'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    GetCandleSticksResponse:
      type: object
      properties:
        cursor:
          type: string
          nullable: true
          description: The cursor to the next page
        page:
          type: number
          description: The page number
        pairAddress:
          type: string
          description: The pair address
        tokenAddress:
          type: string
          nullable: true
          description: The token address
        timeframe:
          type: string
          enum:
            - 1s
            - 10s
            - 30s
            - 1min
            - 5min
            - 10min
            - 30min
            - 1h
            - 4h
            - 12h
            - 1d
            - 1w
            - 1M
          description: The interval of the candle stick
          default: 1min
        currency:
          type: string
          default: usd
          enum:
            - usd
            - native
          description: The currency format
        result:
          description: An array of candlesticks
          type: array
          items:
            $ref: '#/components/schemas/Ohlcv'
      required:
        - page
        - pairAddress
        - tokenAddress
        - timeframe
        - currency
    Ohlcv:
      type: object
      properties:
        timestamp:
          type: string
          nullable: true
          description: ''
        open:
          type: number
          nullable: true
          description: ''
        close:
          type: number
          nullable: true
          description: ''
        high:
          type: number
          nullable: true
          description: ''
        low:
          type: number
          nullable: true
          description: ''
        volume:
          type: number
          nullable: true
          description: ''
        trades:
          type: number
          description: ''
      required:
        - timestamp
        - open
        - close
        - high
        - low
        - volume
        - trades
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````