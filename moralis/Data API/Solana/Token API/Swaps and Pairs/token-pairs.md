> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Pairs

> Get the supported pairs for a specific token address.

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

````yaml /openapi-files/data-api/solana-api.json GET /token/{network}/{address}/pairs
openapi: 3.0.0
info:
  title: Moralis Solana API
  version: '1.0'
servers:
  - url: https://solana-gateway.moralis.io
security: []
paths:
  /token/{network}/{address}/pairs:
    get:
      tags:
        - Token
      summary: Get token pairs by address
      description: Get the supported pairs for a specific token address.
      operationId: getTokenPairs
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
            type: string
            example: So11111111111111111111111111111111111111112
        - name: cursor
          required: false
          in: query
          description: The cursor to the next page
          schema:
            type: string
        - name: limit
          required: false
          in: query
          description: The limit per page
          schema:
            minimum: 1
            maximum: 50
            default: 50
            type: number
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SupportedPairResponse'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    SupportedPairResponse:
      type: object
      properties:
        cursor:
          type: string
          nullable: true
        pageSize:
          type: number
        page:
          type: number
        pairs:
          type: array
          items:
            $ref: '#/components/schemas/SupportedPairInfo'
      required:
        - cursor
        - pageSize
        - page
        - pairs
    SupportedPairInfo:
      type: object
      properties:
        exchangeAddress:
          type: string
        exchangeName:
          type: string
          nullable: true
        exchangeLogo:
          type: string
          nullable: true
        pairAddress:
          type: string
        pairLabel:
          type: string
          nullable: true
        usdPrice:
          type: number
          nullable: true
        usdPrice24hrPercentChange:
          type: number
          nullable: true
        usdPrice24hrUsdChange:
          type: number
          nullable: true
        volume24hrNative:
          type: number
          nullable: true
        volume24hrUsd:
          type: number
          nullable: true
        liquidityUsd:
          type: number
          nullable: true
        inactivePair:
          type: boolean
          nullable: true
        baseToken:
          type: string
        quoteToken:
          type: string
        pair:
          type: array
          items:
            $ref: '#/components/schemas/PairInfo'
      required:
        - exchangeAddress
        - exchangeName
        - exchangeLogo
        - pairAddress
        - pairLabel
        - usdPrice
        - usdPrice24hrPercentChange
        - usdPrice24hrUsdChange
        - volume24hrNative
        - volume24hrUsd
        - liquidityUsd
        - inactivePair
        - baseToken
        - quoteToken
        - pair
    PairInfo:
      type: object
      properties:
        tokenAddress:
          type: string
        tokenName:
          type: string
          nullable: true
        tokenSymbol:
          type: string
          nullable: true
        tokenLogo:
          type: string
          nullable: true
        tokenDecimals:
          type: string
          nullable: true
        pairTokenType:
          type: string
        liquidityUsd:
          type: number
          nullable: true
      required:
        - tokenAddress
        - tokenName
        - tokenSymbol
        - tokenLogo
        - tokenDecimals
        - pairTokenType
        - liquidityUsd
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````