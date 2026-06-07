> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Top Gainers

> Identify tokens with the highest price increases over a period.

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

````yaml /openapi-files/data-api/api.json GET /discovery/tokens/top-gainers
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
  /discovery/tokens/top-gainers:
    get:
      tags:
        - Discovery
      summary: Get tokens with top gainers
      description: Identify tokens with the highest price increases over a period.
      operationId: getTopGainersTokens
      parameters:
        - in: query
          name: chain
          description: The chain to query
          required: false
          schema:
            $ref: '#/components/schemas/chainListWithSolana'
        - in: query
          name: min_market_cap
          description: The minimum market cap in usd of a token
          schema:
            type: number
            example: 50000000
          required: false
        - in: query
          name: security_score
          description: The minimum security score of a token
          schema:
            type: number
            example: 80
          required: false
        - in: query
          name: time_frame
          description: The time frame used for price percent change ordering in response
          required: false
          schema:
            $ref: '#/components/schemas/discoverySupportedTimeFrames'
      responses:
        '200':
          description: Returns the token details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/discoveryTokens'
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
    discoverySupportedTimeFrames:
      type: string
      example: 1d
      enum:
        - 1h
        - 1d
        - 1w
        - 1M
    discoveryTokens:
      type: array
      items:
        required:
          - chain_id
          - token_address
          - token_name
          - token_symbol
          - token_logo
          - price_usd
          - token_age_in_days
          - on_chain_strength_index
          - security_score
          - market_cap
          - fully_diluted_valuation
          - twitter_followers
          - holders_change
          - liquidity_change_usd
          - experienced_net_buyers_change
          - volume_change_usd
          - net_volume_change_usd
          - price_percent_change_usd
        properties:
          chain_id:
            type: string
            description: The chain id of the token
            example: '0x1'
          token_address:
            type: string
            description: The address of the token
            example: '0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2'
          token_name:
            type: string
            description: The name of the token contract
            example: Maker
            nullable: true
          token_symbol:
            type: string
            description: The symbol of the token
            example: MKR
            nullable: true
          token_logo:
            type: string
            description: The logo of the token
            nullable: true
          price_usd:
            type: number
            description: The price in USD for the token
            nullable: true
          token_age_in_days:
            type: number
            description: The number of days since the token was created
            nullable: true
          on_chain_strength_index:
            type: number
            description: The score of coin determined by various on chain metrics
            nullable: true
          security_score:
            type: number
            description: >-
              The security score (0-100) given to the token based various
              parameters
            example: 88
            nullable: true
          market_cap:
            type: number
            description: The market cap in USD
            example: 1351767630.85
            nullable: true
          fully_diluted_valuation:
            type: number
            description: The fully diluted valuation in USD
            example: 1363915420.28
            nullable: true
          twitter_followers:
            type: number
            description: The number of followers of the token on twitter
            example: 255217
            nullable: true
          holders_change:
            $ref: '#/components/schemas/timeFrames'
          liquidity_change_usd:
            $ref: '#/components/schemas/timeFrames'
          experienced_net_buyers_change:
            $ref: '#/components/schemas/timeFrames'
          volume_change_usd:
            $ref: '#/components/schemas/timeFrames'
          net_volume_change_usd:
            $ref: '#/components/schemas/timeFrames'
          price_percent_change_usd:
            $ref: '#/components/schemas/timeFrames'
    timeFrames:
      type: object
      required:
        - 1h
        - 1d
        - 1w
        - 1M
      properties:
        1h:
          type: number
          description: The 1 hour change of the token
          example: 14
          nullable: true
        1d:
          type: number
          description: The 1 day change of the token
          example: 14
          nullable: true
        1w:
          type: number
          description: The 1 week change of the token
          example: 162
          nullable: true
        1M:
          type: number
          description: The 1 month change of the token
          example: 162
          nullable: true
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      x-default: test

````