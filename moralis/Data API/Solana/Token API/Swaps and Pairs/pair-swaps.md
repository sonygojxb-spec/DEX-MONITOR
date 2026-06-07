> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Pair Swaps

> Get all swap related transactions (buy, sell, add liquidity & remove liquidity) for a specific pair address.

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

````yaml /openapi-files/data-api/solana-api.json GET /token/{network}/pairs/{pairAddress}/swaps
openapi: 3.0.0
info:
  title: Moralis Solana API
  version: '1.0'
servers:
  - url: https://solana-gateway.moralis.io
security: []
paths:
  /token/{network}/pairs/{pairAddress}/swaps:
    get:
      tags:
        - Token
      summary: >-
        Get all swap related transactions (buy, sell, add liquidity & remove
        liquidity)
      description: >-
        Get all swap related transactions (buy, sell, add liquidity & remove
        liquidity) for a specific pair address.
      operationId: getSwapsByPairAddress
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
        - name: limit
          required: false
          in: query
          description: The limit per page
          schema:
            minimum: 1
            maximum: 100
            default: 100
            type: number
        - name: cursor
          required: false
          in: query
          description: The cursor to the next page
          schema:
            type: string
        - name: order
          required: false
          in: query
          description: The order of items
          schema:
            default: DESC
            enum:
              - ASC
              - DESC
            type: string
        - name: fromDate
          required: false
          in: query
          description: >-
            The starting date (format in seconds or datestring accepted by
            momentjs)
          schema:
            type: string
        - name: toDate
          required: false
          in: query
          description: >-
            The ending date (format in seconds or datestring accepted by
            momentjs)
          schema:
            type: string
        - name: transactionTypes
          required: false
          in: query
          description: >-
            Transaction types to fetch. Possible values: 'buy', 'sell',
            'addLiquidity' or 'removeLiquidity' separated by comma
          schema:
            default: buy,sell,addLiquidity,removeLiquidity
            example: buy,sell,addLiquidity,removeLiquidity
            type: string
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GetSwapsByPairAddressResponse'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    GetSwapsByPairAddressResponse:
      type: object
      properties:
        page:
          type: number
          example: 1
        pageSize:
          type: number
          example: 100
        cursor:
          type: string
          nullable: true
          example: >-
            eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...kJ8E_653QrA4Q8zb_9OCn6opE9aBo8PjqLeQU_VCaaw
        exchangeName:
          type: string
          nullable: true
          example: Raydium AMM v4
        exchangeLogo:
          type: string
          nullable: true
          example: https://entities-logos.s3.amazonaws.com/raydium.png
        exchangeAddress:
          type: string
          nullable: true
          example: 675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8
        pairLabel:
          type: string
          nullable: true
          example: BREAD/SOL
        pairAddress:
          type: string
          nullable: true
          example: ALeyWh7zN979ZHUWY6YTMJC8wWowzdYqi8RRPRyB3LAd
        baseToken:
          $ref: '#/components/schemas/SwapsByPairAddressTokenMetadata'
        quoteToken:
          $ref: '#/components/schemas/SwapsByPairAddressTokenMetadata'
        result:
          type: array
          items:
            $ref: '#/components/schemas/SwapTransaction'
      required:
        - page
        - pageSize
        - cursor
        - exchangeName
        - exchangeLogo
        - exchangeAddress
        - pairLabel
        - pairAddress
        - baseToken
        - quoteToken
        - result
    SwapsByPairAddressTokenMetadata:
      type: object
      properties:
        address:
          type: string
          nullable: true
          example: madHpjRn6bd8t78Rsy7NuSuNwWa2HU8ByPobZprHbHv
        name:
          type: string
          nullable: true
          example: MAD
        symbol:
          type: string
          nullable: true
          example: MAD
        logo:
          type: string
          nullable: true
          example: >-
            https://ipfs.io/ipfs/QmeCR6o1FrYjczPdDDDm4623usKksjj9BQLu89WqV8jFZW?filename=MAD.jpg
        decimals:
          type: string
          nullable: true
          example: '18'
      required:
        - address
        - name
        - symbol
        - logo
        - decimals
    SwapTransaction:
      type: object
      properties:
        transactionHash:
          type: string
          nullable: true
          example: >-
            3o9NfCBWaDEb8JLJGdp8tfWwXURNokanCvUJf9A9f5nFqmZkRvWcfhkek4t47UhRDSGKHsSzi8MBusin8H7x7YYD
        transactionType:
          type: string
          nullable: true
          example: sell
        transactionIndex:
          type: number
          nullable: true
          example: 250
        subCategory:
          type: string
          nullable: true
          example: sellAll
        blockTimestamp:
          type: string
          nullable: true
          example: '2024-11-28T09:44:55.000Z'
        blockNumber:
          type: number
          example: 304108120
        walletAddress:
          type: string
          nullable: true
          example: A8GVZWGMxRAouFQymPoMKx527JhHKrBRuqFx7NET4j22
        baseTokenAmount:
          type: string
          nullable: true
          example: '199255.444466200'
        quoteTokenAmount:
          type: string
          nullable: true
          example: '0.007374998'
        baseTokenPriceUsd:
          type: number
          example: 0.000008794
        quoteTokenPriceUsd:
          type: number
          example: 237.60336565
        baseQuotePrice:
          type: string
          nullable: true
          example: '0.0000000370127'
        totalValueUsd:
          type: number
          example: 1.752324346
      required:
        - transactionHash
        - transactionType
        - transactionIndex
        - subCategory
        - blockTimestamp
        - blockNumber
        - walletAddress
        - baseTokenAmount
        - quoteTokenAmount
        - baseTokenPriceUsd
        - quoteTokenPriceUsd
        - baseQuotePrice
        - totalValueUsd
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````