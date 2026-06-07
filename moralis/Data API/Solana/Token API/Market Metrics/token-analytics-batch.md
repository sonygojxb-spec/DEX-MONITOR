> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Analytics (Batch)

> Fetch analytics for multiple tokens, including buy volume, sell volume, buyers, sellers, transactions, liquidity and FDV trends over time. Accepts an array of up to 200 tokens, each requiring chain and tokenAddress.

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

<EndpointMeta premium cus={150} mainnetOnly />


## OpenAPI

````yaml /openapi-files/data-api/api.json POST /tokens/analytics
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
  /tokens/analytics:
    post:
      tags:
        - Token
      summary: Get token analytics for a list of token addresses
      description: >-
        Fetch analytics for multiple tokens, including buy volume, sell volume,
        buyers, sellers, transactions, liquidity and FDV trends over time.
        Accepts an array of up to 200 `tokens`, each requiring `chain` and
        `tokenAddress`.
      operationId: getMultipleTokenAnalytics
      requestBody:
        description: Body
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GetMultipleTokenAnalyticsDto'
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MultipleTokenAnalyticsData'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    GetMultipleTokenAnalyticsDto:
      required:
        - tokens
      properties:
        tokens:
          type: array
          maxItems: 200
          description: The tokens to be fetched
          example:
            - chain: '0x1'
              tokenAddress: '0xdac17f958d2ee523a2206206994597c13d831ec7'
            - chain: solana
              tokenAddress: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
          items:
            $ref: '#/components/schemas/tokenAndChainItem'
    MultipleTokenAnalyticsData:
      type: object
      properties:
        categories:
          type: array
          items:
            $ref: '#/components/schemas/TokenAnalyticsData'
    tokenAndChainItem:
      required:
        - chain
        - tokenAddress
      properties:
        chain:
          $ref: '#/components/schemas/chainList'
          type: string
          description: The chain to query
        tokenAddress:
          type: string
          description: The token address
          example: '0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0'
    TokenAnalyticsData:
      type: object
      properties:
        chainId:
          type: string
          description: The chain ID
          example: '0x1'
        categoryId:
          type: string
          example: '0x1'
        totalBuyVolume:
          $ref: '#/components/schemas/VolumeData'
        totalSellVolume:
          $ref: '#/components/schemas/VolumeData'
        totalBuyers:
          $ref: '#/components/schemas/VolumeData'
        totalSellers:
          $ref: '#/components/schemas/VolumeData'
        totalBuys:
          $ref: '#/components/schemas/VolumeData'
        totalSells:
          $ref: '#/components/schemas/VolumeData'
        uniqueWallets:
          $ref: '#/components/schemas/VolumeData'
        pricePercentChange:
          $ref: '#/components/schemas/VolumeData'
        usdPrice:
          type: string
          example: '530'
        totalLiquidity:
          type: string
          example: '530'
        totalFullyDilutedValuation:
          type: string
          example: '530'
    chainList:
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
    VolumeData:
      type: object
      properties:
        5m:
          type: number
          format: double
          example: 6516719.425429553
        1h:
          type: number
          format: double
          example: 137489621.30780438
        6h:
          type: number
          format: double
          example: 585436101.0503464
        24h:
          type: number
          format: double
          example: 2668170156.0409784
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      x-default: test

````