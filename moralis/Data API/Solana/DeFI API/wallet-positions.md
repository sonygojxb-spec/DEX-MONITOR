> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Wallet Positions

> Returns all DeFi positions (lending, liquidity, staking) for a wallet address across specified chains in a unified schema.

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

<EndpointMeta cus={5000} mainnetOnly />


## OpenAPI

````yaml /openapi-files/data-api/api-v1.json GET /v1/wallets/{walletAddress}/defi/positions
openapi: 3.0.0
info:
  title: Moralis Universal API 🚧
  description: This API is in early access and is subject to change.
  version: '1.0'
servers:
  - url: https://api.moralis.com
security: []
externalDocs:
  description: Moralis API Docs
  url: https://docs.moralis.com
paths:
  /v1/wallets/{walletAddress}/defi/positions:
    get:
      tags:
        - DeFi
      summary: Get DeFi positions for a wallet across multiple chains
      description: >-
        Returns all DeFi positions (lending, liquidity, staking) for a wallet
        address across specified chains in a unified schema.
      operationId: getDefiPositions
      parameters:
        - name: walletAddress
          required: true
          in: path
          description: The address
          examples:
            '0xcb1c1fde09f811b294172696404e88e658659905':
              value: '0xcb1c1fde09f811b294172696404e88e658659905'
          schema:
            type: string
        - name: chains
          required: false
          in: query
          description: Chains to query
          schema:
            type: array
            items:
              type: string
              enum:
                - '0x1'
                - ethereum
                - '0x15b38'
                - chiliz
                - '0x19'
                - cro
                - '0x2105'
                - base
                - '0x38'
                - binance
                - '0x440'
                - metis
                - '0x46f'
                - lisk
                - '0x504'
                - moon beam
                - '0x505'
                - moon river
                - '0x531'
                - sei
                - '0x64'
                - gnosis
                - '0x7e4'
                - ronin
                - '0x89'
                - polygon
                - '0x8f'
                - monad
                - '0x92'
                - sonic
                - '0xa'
                - optimism
                - '0xa4b1'
                - arbitrum
                - '0xa86a'
                - avalanche
                - '0xe708'
                - linea
                - '0xfa'
                - fantom
                - solana-mainnet
                - sol
                - all
                - mainnets
                - testnets
        - name: limit
          required: false
          in: query
          description: Maximum number of positions to return per page
          schema:
            minimum: 1
            maximum: 100
            default: 25
            type: number
        - name: cursor
          required: false
          in: query
          description: Pagination cursor for next page
          schema:
            type: string
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UniversalDefiResponseDto'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    UniversalDefiResponseDto:
      type: object
      properties:
        meta:
          $ref: '#/components/schemas/MultiChainResponseMetaDto'
        result:
          type: array
          items:
            $ref: '#/components/schemas/UniversalDefiPositionDto'
        cursor:
          type: string
          description: The cursor to be used for getting the next page of results
          nullable: true
          example: eyJhbGciOi...VCaaw
      required:
        - meta
        - result
        - cursor
    MultiChainResponseMetaDto:
      type: object
      properties:
        syncedAt:
          type: object
          description: >-
            Last sync block position for each chain in the response. The literal
            'latest' indicates the chain is synced up to the latest block (no
            pinned block number available).
          additionalProperties:
            oneOf:
              - type: number
              - type: string
          example:
            '0x1': 1710000000
            solana-mainnet: latest
        unsupportedChains:
          description: Requested chains that are not supported
          nullable: true
          example:
            - '0x89'
          type: array
          items:
            type: string
        failedChains:
          description: Requested chains that are not supported
          nullable: true
          example:
            - '0x89'
          type: array
          items:
            $ref: '#/components/schemas/ChainFailureDto'
      required:
        - syncedAt
        - unsupportedChains
        - failedChains
    UniversalDefiPositionDto:
      type: object
      properties:
        chainId:
          type: string
          example: '0x1'
        protocolId:
          type: string
        protocolName:
          type: string
        protocolUrl:
          type: object
          nullable: true
        protocolLogo:
          type: object
          nullable: true
        position:
          $ref: '#/components/schemas/UniversalDefiPositionBodyDto'
      required:
        - chainId
        - protocolId
        - protocolName
        - position
    ChainFailureDto:
      type: object
      properties:
        chainId:
          type: string
          description: Chain ID of the failed chain
          example: '0x89'
        code:
          type: string
          description: Error code for the failed chain
          example: INTERNAL_SERVER_ERROR
        error:
          type: object
          description: Error message for the failed chain
          example: Failed to fetch data from the chain
          nullable: true
      required:
        - chainId
        - code
        - error
    UniversalDefiPositionBodyDto:
      type: object
      properties:
        label:
          type: string
          enum:
            - lending
            - liquidity
            - staking
            - farming
            - perps
            - vault
            - yield
            - vesting
            - other
        address:
          type: object
          nullable: true
          description: On-chain position identifier (pool, obligation, account)
        tokens:
          type: array
          items:
            $ref: '#/components/schemas/UniversalDefiTokenDto'
        balanceUsd:
          type: object
          nullable: true
        unclaimedUsd:
          type: object
          nullable: true
        details:
          nullable: true
          allOf:
            - $ref: '#/components/schemas/PositionDetailsDto'
      required:
        - label
        - tokens
    UniversalDefiTokenDto:
      type: object
      properties:
        tokenType:
          type: string
          enum:
            - supplied
            - borrowed
            - reward
            - lp
        name:
          type: object
          nullable: true
        symbol:
          type: object
          nullable: true
        address:
          type: string
        decimals:
          type: object
          nullable: true
        logo:
          type: object
          nullable: true
        balance:
          type: object
          nullable: true
        balanceFormatted:
          type: object
          nullable: true
        usdPrice:
          type: object
          nullable: true
        usdValue:
          type: object
          nullable: true
      required:
        - tokenType
        - address
    PositionDetailsDto:
      type: object
      properties:
        type:
          type: string
          enum:
            - lending
            - liquidity
            - staking
            - farming
            - perps
            - vault
            - yield
            - vesting
            - other
        isDebt:
          type: boolean
        lending:
          nullable: true
          allOf:
            - $ref: '#/components/schemas/LendingDetailsDto'
        liquidity:
          nullable: true
          allOf:
            - $ref: '#/components/schemas/LiquidityDetailsDto'
      required:
        - type
        - isDebt
    LendingDetailsDto:
      type: object
      properties:
        healthFactor:
          type: object
          nullable: true
    LiquidityDetailsDto:
      type: object
      properties:
        poolAddress:
          type: object
          nullable: true
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````