> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Filtered Tokens

> Fetch a list of tokens across multiple chains, filtered and ranked by dynamic on-chain metrics like volume, price change, liquidity, holder composition, and more. Supports advanced filters (e.g. “top 10 whales hold <40%”), category-based inclusion/exclusion (e.g. “exclude stablecoins”), and time-based analytics. Ideal for token discovery, investor research, risk analysis, and portfolio tools. Each token returned includes detailed trading metrics as well as on-chain and off-chain metadata.

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

<EndpointMeta cus={250} />

<Warning>
  **Deprecated — scheduled for removal on June 4, 2026.** See the [changelog](/changelog) for details and migration guidance.
</Warning>


## OpenAPI

````yaml /openapi-files/data-api/api.json POST /discovery/tokens
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
  /discovery/tokens:
    post:
      tags:
        - Discovery
      summary: Returns a list of tokens that match the specified filters and criteria
      description: >-
        Fetch a list of tokens across multiple chains, filtered and ranked by
        dynamic on-chain metrics like volume, price change, liquidity, holder
        composition, and more. Supports advanced filters (e.g. “top 10 whales
        hold <40%”), category-based inclusion/exclusion (e.g. “exclude
        stablecoins”), and time-based analytics. Ideal for token discovery,
        investor research, risk analysis, and portfolio tools. Each token
        returned includes detailed trading metrics as well as on-chain and
        off-chain metadata.
      operationId: getFilteredTokens
      parameters: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                chain:
                  type: string
                  example: '0x1'
                  description: The blockchain identifier
                chains:
                  type: array
                  items:
                    $ref: '#/components/schemas/chainListWithSolana'
                filters:
                  type: array
                  description: List of filters to apply
                  items:
                    type: object
                    example:
                      metric: experiencedBuyers
                      timeFrame: oneMonth
                      gt: 100
                    properties:
                      metric:
                        $ref: '#/components/schemas/tokenExplorerMetrics'
                        example: experiencedBuyers
                        description: The metric to filter on
                      timeFrame:
                        $ref: '#/components/schemas/tokenExplorerTimeFrames'
                        type: string
                        example: oneMonth
                        description: The time frame for the filter
                      gt:
                        type: number
                        example: 10
                        description: Greater-than value for the filter
                      lt:
                        type: number
                        example: 10
                        description: Less-than value for the filter
                      eq:
                        type: number
                        example: 10
                        description: Equal-to value for the filter
                    required:
                      - metric
                      - timeFrame
                sortBy:
                  type: object
                  description: Metric and time frame to sort by
                  properties:
                    metric:
                      $ref: '#/components/schemas/tokenExplorerMetrics'
                      type: string
                      example: experiencedBuyers
                      description: The metric to sort by
                    timeFrame:
                      $ref: '#/components/schemas/tokenExplorerTimeFrames'
                      type: string
                      example: oneHour
                      description: The time frame for sorting
                    type:
                      type: string
                      enum:
                        - ASC
                        - DESC
                      example: DESC
                      description: The order of sorting
                  required:
                    - metric
                    - timeFrame
                    - type
                categories:
                  type: object
                  description: Categories to filter tokens
                  properties:
                    include:
                      type: array
                      items:
                        type: string
                    exclude:
                      type: array
                      items:
                        type: string
                timeFramesToReturn:
                  type: array
                  items:
                    $ref: '#/components/schemas/tokenExplorerTimeFrames'
                    type: string
                  example: []
                  description: List of time frames to return in the response
                metricsToReturn:
                  type: array
                  items:
                    $ref: '#/components/schemas/tokenExplorerMetrics'
                    type: string
                  example: []
                  description: List of metrics to return in the response
                excludeMetadata:
                  type: boolean
                  example: false
                  description: Whether to exclude metadata from the response
                limit:
                  type: number
                  example: 100
                  description: Maximum number of results
              required:
                - chain
                - filters
                - sortBy
                - limit
      responses:
        '200':
          description: Returns the token details
          content:
            application/json:
              schema:
                type: object
                properties:
                  metadata:
                    type: object
                    properties:
                      tokenAddress:
                        type: string
                        example: '0x55d398326f99059ff775485246999027b3197955'
                      chainId:
                        type: string
                        example: '0x1'
                      name:
                        type: string
                        example: Tether USD
                      symbol:
                        type: string
                        example: USDT
                      decimals:
                        type: number
                        example: 18
                      logo:
                        type: string
                        example: https://example.com/logo.png
                      blockNumberMinted:
                        type: number
                        example: 176416
                      usdPrice:
                        type: number
                        example: 0.9982436729635321
                      security:
                        type: object
                        properties:
                          isOpenSource:
                            type: boolean
                            example: true
                          isProxy:
                            type: boolean
                            example: false
                          isMintable:
                            type: boolean
                            example: true
                          hiddenOwner:
                            type: boolean
                            example: false
                          buyTax:
                            type: string
                            example: '0'
                          sellTax:
                            type: string
                            example: '0'
                          cannotBuy:
                            type: boolean
                            example: false
                          cannotSellAll:
                            type: boolean
                            example: false
                          isHoneyPot:
                            type: boolean
                            example: false
                          securityScore:
                            type: number
                            example: 70
                          possibleSpam:
                            type: boolean
                            example: false
                      totalSupply:
                        type: string
                        example: '1000000000'
                      fullyDilutedValue:
                        type: number
                        example: 1000000000
                      circulatingSupply:
                        type: number
                        example: 1000000000
                      marketCap:
                        type: number
                        example: 1000000000
                      totalHolders:
                        type: number
                        example: 100000
                      totalLiquidityUsd:
                        type: number
                        example: 100000
                      links:
                        $ref: '#/components/schemas/discoveryTokenLinks'
                      categories:
                        type: array
                        items:
                          type: string
                  metrics:
                    type: object
      deprecated: true
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
    tokenExplorerMetrics:
      type: string
      enum:
        - experiencedBuyers
        - tokenAge
        - holders
        - buyers
        - sellers
        - netBuyers
        - experiencedSellers
        - netExperiencedBuyers
        - fullyDilutedValuation
        - marketCap
        - usdPrice
        - usdPricePercentChange
        - liquidityChange
        - liquidityChangeUSD
        - volumeUsd
        - buyVolumeUsd
        - sellVolumeUsd
        - netVolumeUsd
        - securityScore
        - totalHolders
        - totalLiquidityUsd
    tokenExplorerTimeFrames:
      type: string
      enum:
        - oneMonth
        - tenMinutes
        - thirtyMinutes
        - oneHour
        - fourHours
        - twelveHours
        - oneDay
        - oneWeek
    discoveryTokenLinks:
      type: object
      required:
        - bitbucket
        - discord
        - facebook
        - github
        - instagram
        - linkedin
        - medium
        - reddit
        - telegram
        - tiktok
        - twitter
        - website
        - youtube
      properties:
        bitbucket:
          type: string
          description: The link of the token on the platform
        discord:
          type: string
          description: The link of the token on the platform
        facebook:
          type: string
          description: The link of the token on the platform
        github:
          type: string
          description: The link of the token on the platform
        instagram:
          type: string
          description: The link of the token on the platform
        linkedin:
          type: string
          description: The link of the token on the platform
        medium:
          type: string
          description: The link of the token on the platform
        reddit:
          type: string
          description: The link of the token on the platform
        telegram:
          type: string
          description: The link of the token on the platform
        tiktok:
          type: string
          description: The link of the token on the platform
        twitter:
          type: string
          description: The link of the token on the platform
        website:
          type: string
          description: The link of the token on the platform
        youtube:
          type: string
          description: The link of the token on the platform
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      x-default: test

````