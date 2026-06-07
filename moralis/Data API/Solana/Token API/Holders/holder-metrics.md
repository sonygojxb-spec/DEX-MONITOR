> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Holder Metrics

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

````yaml /openapi-files/data-api/solana-api.json GET /token/{network}/holders/{address}
openapi: 3.0.0
info:
  title: Moralis Solana API
  version: '1.0'
servers:
  - url: https://solana-gateway.moralis.io
security: []
paths:
  /token/{network}/holders/{address}:
    get:
      tags:
        - Token
      summary: Get the summary of holders for a given token token.
      operationId: getTokenHolders
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
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GetTokenHoldersResponseDto'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    GetTokenHoldersResponseDto:
      type: object
      properties:
        totalHolders:
          type: number
          example: 5000
        holdersByAcquisition:
          $ref: '#/components/schemas/HoldersByAcquisitionDto'
        holderChange:
          $ref: '#/components/schemas/HolderChangeSummaryDTO'
        holderDistribution:
          $ref: '#/components/schemas/HolderDistributionDto'
        holderSupply:
          $ref: '#/components/schemas/HolderSupplyDto'
      required:
        - totalHolders
        - holdersByAcquisition
        - holderChange
        - holderDistribution
        - holderSupply
    HoldersByAcquisitionDto:
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
    HolderChangeSummaryDTO:
      type: object
      properties:
        5min:
          $ref: '#/components/schemas/HolderChangeDto'
        1h:
          $ref: '#/components/schemas/HolderChangeDto'
        6h:
          $ref: '#/components/schemas/HolderChangeDto'
        24h:
          $ref: '#/components/schemas/HolderChangeDto'
        3d:
          $ref: '#/components/schemas/HolderChangeDto'
        7d:
          $ref: '#/components/schemas/HolderChangeDto'
        30d:
          $ref: '#/components/schemas/HolderChangeDto'
      required:
        - 5min
        - 1h
        - 6h
        - 24h
        - 3d
        - 7d
        - 30d
    HolderDistributionDto:
      type: object
      properties:
        whales:
          type: number
          example: 150
        sharks:
          type: number
          example: 150
        dolphins:
          type: number
          example: 150
        fish:
          type: number
          example: 150
        octopus:
          type: number
          example: 150
        crabs:
          type: number
          example: 150
        shrimps:
          type: number
          example: 150
      required:
        - whales
        - sharks
        - dolphins
        - fish
        - octopus
        - crabs
        - shrimps
    HolderSupplyDto:
      type: object
      properties:
        top10:
          $ref: '#/components/schemas/HolderSupplyChangeDto'
        top25:
          $ref: '#/components/schemas/HolderSupplyChangeDto'
        top50:
          $ref: '#/components/schemas/HolderSupplyChangeDto'
        top100:
          $ref: '#/components/schemas/HolderSupplyChangeDto'
        top250:
          $ref: '#/components/schemas/HolderSupplyChangeDto'
        top500:
          $ref: '#/components/schemas/HolderSupplyChangeDto'
      required:
        - top10
        - top25
        - top50
        - top100
        - top250
        - top500
    HolderChangeDto:
      type: object
      properties:
        change:
          type: number
          example: 50
        changePercent:
          type: number
          example: 2.5
      required:
        - change
        - changePercent
    HolderSupplyChangeDto:
      type: object
      properties:
        supply:
          type: string
          example: '1000000.123456'
        supplyPercent:
          type: number
          example: 12.5
      required:
        - supply
        - supplyPercent
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````