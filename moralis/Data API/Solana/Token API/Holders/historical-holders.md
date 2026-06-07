> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Historical Token Holders

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

<EndpointMeta cus={50} />


## OpenAPI

````yaml /openapi-files/data-api/solana-api.json GET /token/{network}/holders/{address}/historical
openapi: 3.0.0
info:
  title: Moralis Solana API
  version: '1.0'
servers:
  - url: https://solana-gateway.moralis.io
security: []
paths:
  /token/{network}/holders/{address}/historical:
    get:
      tags:
        - Token
      summary: Get token holders overtime for a given tokens
      operationId: getHistoricalTokenHolders
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
            example: 6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN
            type: string
        - name: cursor
          required: false
          in: query
          description: The cursor to the next page
          schema:
            type: string
        - name: timeFrame
          required: true
          in: query
          description: The interval of the holders data
          schema:
            default: 1min
            enum:
              - 1min
              - 5min
              - 10min
              - 30min
              - 1h
              - 4h
              - 12h
              - 1d
              - 1w
              - 1m
            type: string
        - name: fromDate
          required: true
          in: query
          description: >-
            The starting date (format in seconds or datestring accepted by
            momentjs)
          schema:
            type: string
        - name: toDate
          required: true
          in: query
          description: >-
            The ending date (format in seconds or datestring accepted by
            momentjs)
          schema:
            type: string
        - name: limit
          required: false
          in: query
          description: The limit per page depending on the plan
          schema:
            default: 100
            type: number
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GetHistoricalHoldersResponseDto'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    GetHistoricalHoldersResponseDto:
      type: object
      properties:
        cursor:
          type: string
          description: The cursor to the next page
        result:
          type: array
          items:
            $ref: '#/components/schemas/HolderTimelineItemDto'
        page:
          type: number
          description: The current page number
      required:
        - result
        - page
    HolderTimelineItemDto:
      type: object
      properties:
        timestamp:
          type: string
          example: '2025-02-25T00:00:00Z'
        totalHolders:
          type: number
          example: 2000
        netHolderChange:
          type: number
          example: 50
        holderPercentChange:
          type: number
          example: 2.5
        newHoldersByAcquisition:
          $ref: '#/components/schemas/NewHoldersByAcquisitionDTO'
        holdersIn:
          $ref: '#/components/schemas/HolderCategoryDTO'
        holdersOut:
          $ref: '#/components/schemas/HolderCategoryDTO'
      required:
        - timestamp
        - totalHolders
        - netHolderChange
        - holderPercentChange
        - newHoldersByAcquisition
        - holdersIn
        - holdersOut
    NewHoldersByAcquisitionDTO:
      type: object
      properties:
        swap:
          type: number
          example: 150
        transfer:
          type: number
          example: 50
        airdrop:
          type: number
          example: 20
      required:
        - swap
        - transfer
        - airdrop
    HolderCategoryDTO:
      type: object
      properties:
        whales:
          type: number
          example: 5
        sharks:
          type: number
          example: 12
        dolphins:
          type: number
          example: 20
        fish:
          type: number
          example: 100
        octopus:
          type: number
          example: 50
        crabs:
          type: number
          example: 200
        shrimps:
          type: number
          example: 1000
      required:
        - whales
        - sharks
        - dolphins
        - fish
        - octopus
        - crabs
        - shrimps
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````