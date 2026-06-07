> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Score

> Retrieve a score for a specific token along with detailed metrics including price, volume, liquidity, transaction counts, and supply information.

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

<EndpointMeta cus={100} mainnetOnly />


## OpenAPI

````yaml /openapi-files/data-api/api.json GET /tokens/{tokenAddress}/score
openapi: 3.0.0
info:
  title: EVM API
  version: '2.2'
servers:
  - url: https://deep-index.moralis.io/api/v2.2
security:
  - ApiKeyAuth: []
tags: []
paths:
  /tokens/{tokenAddress}/score:
    get:
      tags:
        - Token
      summary: Get token score by token address
      description: >-
        Retrieve a score for a specific token along with detailed metrics
        including price, volume, liquidity, transaction counts, and supply
        information.
      operationId: getTokenScore
      parameters:
        - in: query
          name: chain
          description: The chain to query
          required: false
          schema:
            $ref: '#/components/schemas/chainListWithSolana'
        - in: path
          name: tokenAddress
          description: The token address to query
          required: true
          schema:
            type: string
            example: '0x6982508145454ce325ddbe47a25d4ec3d2311933'
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TokenScoreResponse'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    chainListWithSolana:
      type: string
      example: eth
      default: eth
      enum:
        - eth
        - '0x1'
        - sepolia
        - '0xaa36a7'
        - polygon
        - '0x89'
        - bsc
        - '0x38'
        - bsc testnet
        - '0x61'
        - avalanche
        - '0xa86a'
        - fantom
        - '0xfa'
        - cronos
        - '0x19'
        - arbitrum
        - '0xa4b1'
        - chiliz
        - '0x15b38'
        - chiliz testnet
        - '0x15b32'
        - gnosis
        - '0x64'
        - gnosis testnet
        - '0x27d8'
        - base
        - '0x2105'
        - base sepolia
        - '0x14a34'
        - optimism
        - '0xa'
        - polygon amoy
        - '0x13882'
        - linea
        - '0xe708'
        - moonbeam
        - '0x504'
        - moonriver
        - '0x505'
        - moonbase
        - '0x507'
        - linea sepolia
        - '0xe705'
        - flow
        - '0x2eb'
        - flow-testnet
        - '0x221'
        - ronin
        - '0x7e4'
        - ronin-testnet
        - '0x31769'
        - lisk
        - '0x46f'
        - lisk-sepolia
        - '0x106a'
        - pulse
        - '0x171'
        - sei-testnet
        - '0x530'
        - sei
        - '0x531'
        - monad
        - '0x8f'
        - solana
    TokenScoreResponse:
      type: object
      properties:
        tokenAddress:
          type: string
          example: '0x6982508145454ce325ddbe47a25d4ec3d2311933'
        chainId:
          type: string
          example: '0x1'
        score:
          type: integer
          example: 94
        updatedAt:
          type: string
          example: '2025-12-03T21:10:28Z'
        metrics:
          $ref: '#/components/schemas/TokenScoreMetrics'
          nullable: true
    TokenScoreMetrics:
      type: object
      properties:
        usdPrice:
          type: number
          example: 0.00000647147501365255
        liquidityUsd:
          type: number
          example: 10890420.9
        volumeUsd:
          $ref: '#/components/schemas/TokenScoreVolumeUsd'
        transactions:
          $ref: '#/components/schemas/TokenScoreTransactions'
        supply:
          $ref: '#/components/schemas/TokenScoreSupply'
    TokenScoreVolumeUsd:
      type: object
      properties:
        10m:
          type: number
          example: 17506.72
        30m:
          type: number
          example: 974862.35
        1h:
          type: number
          example: 88701.15
        4h:
          type: number
          example: 84547204.23
        12h:
          type: number
          example: 974862.35
        1d:
          type: number
          example: 1971902.13
        7d:
          type: number
          example: 4571941.67
        30d:
          type: number
          example: 445.57
    TokenScoreTransactions:
      type: object
      properties:
        10m:
          type: number
          example: 54
        30m:
          type: number
          example: 132
        1h:
          type: number
          example: 3040
        4h:
          type: number
          example: 85301
        12h:
          type: number
          example: 1602
        1d:
          type: number
          example: 602
        7d:
          type: number
          example: 15328
        30d:
          type: number
          example: 25
    TokenScoreSupply:
      type: object
      properties:
        total:
          type: number
          example: 420689899653542.56
        top10Percent:
          type: number
          example: 41.03
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      x-default: test

````