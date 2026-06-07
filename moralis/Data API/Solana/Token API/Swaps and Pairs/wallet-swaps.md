> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Wallet Swaps

> Get all swap related transactions (buy, sell) for a specific wallet address.

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

````yaml /openapi-files/data-api/solana-api.json GET /account/{network}/{address}/swaps
openapi: 3.0.0
info:
  title: Moralis Solana API
  version: '1.0'
servers:
  - url: https://solana-gateway.moralis.io
security: []
paths:
  /account/{network}/{address}/swaps:
    get:
      tags:
        - Account
      summary: >-
        Get all swap related transactions (buy, sell) for a specific wallet
        address.
      description: >-
        Get all swap related transactions (buy, sell) for a specific wallet
        address.
      operationId: getSwapsByWalletAddress
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
            example: kXB7FfzdrfZpAZEW3TZcp8a8CwQbsowa6BdfAHZ4gVs
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
            Transaction types to fetch. Possible values: 'buy','sell' or both
            separated by comma
          schema:
            default: buy,sell
            example: buy,sell
            type: string
        - name: tokenAddress
          required: false
          in: query
          description: Token address to get transactions for
          schema:
            type: string
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GetSwapsByWalletAddressResponseDto'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    GetSwapsByWalletAddressResponseDto:
      type: object
      properties:
        page:
          type: number
        pageSize:
          type: number
        cursor:
          type: string
          nullable: true
        result:
          type: array
          items:
            $ref: '#/components/schemas/SwapTransactionForWalletAndTokenDto'
      required:
        - page
        - pageSize
        - cursor
        - result
    SwapTransactionForWalletAndTokenDto:
      type: object
      properties:
        transactionHash:
          type: string
          example: '0xafc66b9b1802618f560be5244395f0fc0b95a1f1fdeee7a206acbb546c9e8a72'
        transactionIndex:
          type: number
          example: 5
        transactionType:
          type: string
          example: buy
        blockNumber:
          type: number
          example: 12345678
        blockTimestamp:
          type: string
          example: '2024-11-21T09:22:28.000Z'
        subCategory:
          type: string
          nullable: true
          example: ACCUMULATION
        walletAddress:
          type: string
          example: '0x1c584a6baecb7c5d51caa0ef3a579e08bd49d4e5'
        pairAddress:
          type: string
          nullable: true
          example: '0xdded227d71a096c6b5d87807c1b5c456771aaa94'
        pairLabel:
          type: string
          nullable: true
          example: USDC/WETH
        exchangeAddress:
          type: string
          nullable: true
          example: '0x1080ee857d165186af7f8d63e8ec510c28a6d1ea'
        exchangeName:
          type: string
          nullable: true
          example: Uniswap
        exchangeLogo:
          type: string
          nullable: true
          example: >-
            https://logo.moralis.io/0xe708_0xe5d7c2a44ffddf6b295a15c148167daaaf5cf34f_769a0b766bd3d6d1830f0a95d7b3e313
        baseToken:
          type: string
          nullable: true
          example: ETH
        quoteToken:
          type: string
          nullable: true
          example: USDT
        bought:
          nullable: true
          example:
            address: '0xe5d7c2a44ffddf6b295a15c148167daaaf5cf34f'
            name: Wrapped Ether
            symbol: SYM
            logo: https://example.com/logo-token1.png
            amount: '0.000014332429005002'
            usdPrice: 3148.1828278180296
            usdAmount: 1230
            tokenType: token1
          allOf:
            - $ref: '#/components/schemas/SwapTokenMetadataDto'
        sold:
          nullable: true
          example:
            address: '0x176211869ca2b568f2a7d4ee941e073a821ee1ff'
            name: USDC
            symbol: SYM
            logo: https://example.com/logo-token2.png
            amount: '1000'
            usdPrice: 0.9999999999999986
            usdAmount: -0.045138999999999936
            tokenType: token0
          allOf:
            - $ref: '#/components/schemas/SwapTokenMetadataDto'
        baseQuotePrice:
          type: string
          nullable: true
          example: '0.01'
        totalValueUsd:
          type: number
          nullable: true
          example: 1230
      required:
        - transactionHash
        - transactionIndex
        - transactionType
        - blockNumber
        - blockTimestamp
        - subCategory
        - walletAddress
        - pairAddress
        - pairLabel
        - exchangeAddress
        - exchangeName
        - exchangeLogo
        - baseToken
        - quoteToken
        - bought
        - sold
        - baseQuotePrice
        - totalValueUsd
    SwapTokenMetadataDto:
      type: object
      properties:
        address:
          type: string
          nullable: true
          example: '0xe5d7c2a44ffddf6b295a15c148167daaaf5cf34f'
        name:
          type: string
          nullable: true
          example: Wrapped Ether
        symbol:
          type: string
          nullable: true
          example: WETH
        logo:
          type: string
          nullable: true
          example: >-
            https://logo.moralis.io/0xe708_0xe5d7c2a44ffddf6b295a15c148167daaaf5cf34f_769a0b766bd3d6d1830f0a95d7b3e313
        amount:
          type: string
          nullable: true
          example: '0.000014332429005002'
        usdPrice:
          type: number
          nullable: true
          example: 3148.1828278180296
        usdAmount:
          type: number
          nullable: true
          example: 0.0123
        tokenType:
          type: string
          nullable: true
          example: token1
      required:
        - address
        - name
        - symbol
        - logo
        - amount
        - usdPrice
        - usdAmount
        - tokenType
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````