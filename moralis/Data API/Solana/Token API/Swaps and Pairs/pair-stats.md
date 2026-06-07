> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Pair Stats

> Gets the stats for a specific pair address

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

<EndpointMeta cus={100} />


## OpenAPI

````yaml /openapi-files/data-api/solana-api.json GET /token/{network}/pairs/{pairAddress}/stats
openapi: 3.0.0
info:
  title: Moralis Solana API
  version: '1.0'
servers:
  - url: https://solana-gateway.moralis.io
security: []
paths:
  /token/{network}/pairs/{pairAddress}/stats:
    get:
      tags:
        - Token
      summary: Get stats for a pair address
      description: Gets the stats for a specific pair address
      operationId: getPairStats
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
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GetPairStatsResponse'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    GetPairStatsResponse:
      type: object
      properties:
        tokenAddress:
          type: string
          description: The token address
        tokenName:
          type: string
          nullable: true
          description: The token name
        tokenSymbol:
          type: string
          nullable: true
          description: The token symbol
        tokenLogo:
          type: string
          nullable: true
          description: The token logo
        pairCreated:
          type: string
          nullable: true
          description: The timestamp when pair is created
        pairLabel:
          type: string
          nullable: true
          description: The pair label
        pairAddress:
          type: string
          description: The pair address
        exchange:
          type: string
          nullable: true
          description: The exchange name
        exchangeAddress:
          type: string
          description: The exchange address
        exchangeLogo:
          type: string
          nullable: true
          description: The exchange logo
        exchangeUrl:
          type: string
          nullable: true
          description: The exchange url
        currentUsdPrice:
          type: string
          nullable: true
          description: The current usd price of the token
        currentNativePrice:
          type: string
          nullable: true
          description: The current native price of the token
        totalLiquidityUsd:
          type: string
          nullable: true
          description: The total liquidity of the pair in USD
        pricePercentChange:
          description: The price percent change stats
          allOf:
            - $ref: '#/components/schemas/PairStats'
        liquidityPercentChange:
          description: The liquidity change stats
          allOf:
            - $ref: '#/components/schemas/PairStats'
        buys:
          description: The total buys stats
          allOf:
            - $ref: '#/components/schemas/PairStats'
        sells:
          description: The total sells stats
          allOf:
            - $ref: '#/components/schemas/PairStats'
        totalVolume:
          description: The total volume stats
          allOf:
            - $ref: '#/components/schemas/PairStats'
        buyVolume:
          description: The total buy volume stats
          allOf:
            - $ref: '#/components/schemas/PairStats'
        sellVolume:
          description: The total sell volume stats
          allOf:
            - $ref: '#/components/schemas/PairStats'
        buyers:
          description: The total unique buyers stats
          allOf:
            - $ref: '#/components/schemas/PairStats'
        sellers:
          description: The total unique sellers stats
          allOf:
            - $ref: '#/components/schemas/PairStats'
      required:
        - tokenAddress
        - tokenName
        - tokenSymbol
        - tokenLogo
        - pairCreated
        - pairLabel
        - pairAddress
        - exchange
        - exchangeAddress
        - exchangeLogo
        - exchangeUrl
        - currentUsdPrice
        - currentNativePrice
        - totalLiquidityUsd
        - pricePercentChange
        - liquidityPercentChange
        - buys
        - sells
        - totalVolume
        - buyVolume
        - sellVolume
        - buyers
        - sellers
    PairStats:
      type: object
      properties:
        5min:
          type: number
          nullable: true
          description: The 5 minutes timeframe data
        1h:
          type: number
          nullable: true
          description: The 1 hour timeframe data
        4h:
          type: number
          nullable: true
          description: The 4 hours timeframe data
        24h:
          type: number
          nullable: true
          description: The 24 hours timeframe data
      required:
        - 5min
        - 1h
        - 4h
        - 24h
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````