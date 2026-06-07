> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Snipers

> Get all snipers.

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

<Warning>
  **Deprecated — scheduled for removal on June 4, 2026.** See the [changelog](/changelog) for details and migration guidance.
</Warning>


## OpenAPI

````yaml /openapi-files/data-api/solana-api.json GET /token/{network}/pairs/{pairAddress}/snipers
openapi: 3.0.0
info:
  title: Moralis Solana API
  version: '1.0'
servers:
  - url: https://solana-gateway.moralis.io
security: []
paths:
  /token/{network}/pairs/{pairAddress}/snipers:
    get:
      tags:
        - Token
      summary: Get snipers by pair address.
      description: Get all snipers.
      operationId: getSnipersByPairAddress
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
        - name: pairAddress
          required: true
          in: path
          description: The address of the pair to query
          schema:
            example: Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE
            type: string
        - name: blocksAfterCreation
          required: false
          in: query
          schema:
            type: number
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GetSnipersResponse'
      deprecated: true
      security:
        - ApiKeyAuth: []
components:
  schemas:
    GetSnipersResponse:
      type: object
      properties:
        transactionHash:
          type: string
        blockNumber:
          type: number
        blockTimestamp:
          type: string
        result:
          type: array
          items:
            $ref: '#/components/schemas/SniperResponse'
      required:
        - transactionHash
        - blockNumber
        - blockTimestamp
        - result
    SniperResponse:
      type: object
      properties:
        walletAddress:
          type: string
        totalTokensSniped:
          type: number
        totalSnipedUsd:
          type: number
        totalSnipedTransactions:
          type: number
        snipedTransactions:
          type: array
          items:
            $ref: '#/components/schemas/SniperTransaction'
        totalTokensSold:
          type: number
        totalSoldUsd:
          type: number
        totalSellTransactions:
          type: number
        sellTransactions:
          type: array
          items:
            $ref: '#/components/schemas/SniperTransaction'
        currentBalance:
          type: number
        currentBalanceUsdValue:
          type: number
        realizedProfitPercentage:
          type: number
        realizedProfitUsd:
          type: number
      required:
        - walletAddress
        - totalTokensSniped
        - totalSnipedUsd
        - totalSnipedTransactions
        - snipedTransactions
        - totalTokensSold
        - totalSoldUsd
        - totalSellTransactions
        - sellTransactions
        - currentBalance
        - currentBalanceUsdValue
        - realizedProfitPercentage
        - realizedProfitUsd
    SniperTransaction:
      type: object
      properties:
        transactionHash:
          type: string
        transactionTimestamp:
          type: string
        blocksAfterCreation:
          type: number
      required:
        - transactionHash
        - transactionTimestamp
        - blocksAfterCreation
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````