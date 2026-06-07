> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Search

> Search for tokens using their contract address, pair address, name, or symbol. Cross-chain by default with support to filter by chains. Additional options to sortBy various metrics, such as market cap, liquidity or volume.

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

<EndpointMeta cus={150} mainnetOnly />


## OpenAPI

````yaml /openapi-files/data-api/api.json GET /tokens/search
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
  /tokens/search:
    get:
      tags:
        - Token
      summary: >-
        Search for tokens based on contract address, pair address, token name or
        token symbol.
      description: >-
        Search for tokens using their contract address, pair address, name, or
        symbol. Cross-chain by default with support to filter by `chains`.
        Additional options to `sortBy` various metrics, such as market cap,
        liquidity or volume.
      operationId: searchTokens
      parameters:
        - in: query
          name: chains
          description: The chains to query
          required: false
          schema:
            type: string
        - in: query
          name: query
          description: The query to search
          required: true
          schema:
            type: string
            example: pepe
        - in: query
          name: limit
          description: The desired page size of the result.
          required: false
          schema:
            type: number
        - in: query
          name: isVerifiedContract
          description: True to include only verified contracts
          required: false
          schema:
            type: boolean
            default: false
        - in: query
          name: sortBy
          description: Sort by volume1hDesc, volume24hDesc, liquidityDesc, marketCapDesc
          required: false
          schema:
            type: string
            example: volume1hDesc
            default: volume1hDesc
            enum:
              - volume1hDesc
              - volume24hDesc
              - liquidityDesc
              - marketCapDesc
        - in: query
          name: boostVerifiedContracts
          description: True to boost verified contracts
          required: false
          schema:
            type: boolean
            default: true
      responses:
        '200':
          description: Returns the search results
          content:
            application/json:
              schema:
                type: object
                properties:
                  total:
                    type: integer
                    example: 10000
                  result:
                    type: array
                    items:
                      type: object
                      properties:
                        tokenAddress:
                          type: string
                          example: '0x6982508145454ce325ddbe47a25d4ec3d2311933'
                        chainId:
                          type: string
                          example: '0x1'
                        name:
                          type: string
                          example: Pepe
                        symbol:
                          type: string
                          example: PEPE
                        blockNumber:
                          type: integer
                          example: 17046105
                        blockTimestamp:
                          type: integer
                          example: 1681483883
                        usdPrice:
                          type: number
                          format: float
                          example: 0.000024509478199144
                        marketCap:
                          type: number
                          format: float
                          example: 9825629287.860994
                        experiencedNetBuyers:
                          type: object
                          properties:
                            oneHour:
                              type: integer
                              example: 31
                            oneDay:
                              type: integer
                              example: 51
                            oneWeek:
                              type: integer
                              example: 77
                        netVolumeUsd:
                          type: object
                          properties:
                            oneHour:
                              type: number
                              format: float
                              example: 188552.0639107914
                            oneDay:
                              type: number
                              format: float
                              example: 1188552.0639107914
                        liquidityChangeUSD:
                          type: object
                          properties:
                            oneHour:
                              type: number
                              format: float
                              example: -287308.4496394396
                            oneDay:
                              type: number
                              format: float
                              example: -387308.4496394396
                        usdPricePercentChange:
                          type: object
                          properties:
                            oneHour:
                              type: number
                              format: float
                              example: 1.079210724244654
                            oneDay:
                              type: number
                              format: float
                              example: 2.079210724244654
                        volumeUsd:
                          type: object
                          properties:
                            oneHour:
                              type: number
                              format: float
                              example: 188552.0639107914
                            oneDay:
                              type: number
                              format: float
                              example: 76927981.5281831
                        securityScore:
                          type: integer
                          example: 92
                        logo:
                          type: string
                          nullable: true
                          example: >-
                            https://adds-token-info-29a861f.s3.eu-central-1.amazonaws.com/marketing/evm/0x6982508145454ce325ddbe47a25d4ec3d2311933_icon.png
                        isVerifiedContract:
                          type: boolean
                          example: false
                        fullyDilutedValuation:
                          type: number
                          format: float
                          example: 71242582.97741453
                        totalHolders:
                          type: number
                          format: float
                          example: 18908
                        totalLiquidityUsd:
                          type: number
                          format: float
                          example: 18908.234
                        implementations:
                          type: array
                          items:
                            description: >-
                              The token addresses of the same symbol from
                              another chains
                            required:
                              - chainId
                              - address
                            properties:
                              chainId:
                                type: string
                                description: The chain id
                                example: '0x1'
                              chain:
                                type: string
                                description: The chain name
                                example: eth
                              chainName:
                                type: string
                                description: The chain name
                                example: Ethereum
                              address:
                                type: string
                                description: The token address
                                example: '0x6982508145454ce325ddbe47a25d4ec3d2311933'
      security:
        - ApiKeyAuth: []
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      x-default: test

````