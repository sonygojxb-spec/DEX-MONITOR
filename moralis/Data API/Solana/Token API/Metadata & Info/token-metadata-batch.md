> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Token Metadata (Batch)

> Get multiple global token metadata for a given network and contract (mint, standard, name, symbol, metaplex). Supports up to 100 tokens per request.

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

````yaml /openapi-files/data-api/solana-api.json POST /token/{network}/metadata
openapi: 3.0.0
info:
  title: Moralis Solana API
  version: '1.0'
servers:
  - url: https://solana-gateway.moralis.io
security: []
paths:
  /token/{network}/metadata:
    post:
      tags:
        - Token
      summary: Get multiple token metadata
      description: >-
        Get multiple global token metadata for a given network and contract
        (mint, standard, name, symbol, metaplex).
      operationId: getMultipleTokenMetadata
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
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/GetMultipleTokenMetadtaRequest'
      responses:
        '201':
          description: ''
        default:
          description: ''
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/TokenMetadata'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    GetMultipleTokenMetadtaRequest:
      type: object
      properties:
        addresses:
          minItems: 1
          maxItems: 100
          example:
            - So11111111111111111111111111111111111111112
          type: array
          items:
            type: string
      required:
        - addresses
    TokenMetadata:
      type: object
      properties:
        mint:
          type: string
        standard:
          type: string
        name:
          type: string
          nullable: true
        symbol:
          type: string
          nullable: true
        logo:
          type: string
          nullable: true
        decimals:
          type: string
          nullable: true
        tokenStandard:
          type: number
          nullable: true
        score:
          type: number
          nullable: true
        totalSupply:
          type: string
          nullable: true
        totalSupplyFormatted:
          type: string
          nullable: true
        fullyDilutedValue:
          type: string
          nullable: true
        marketCap:
          type: string
          nullable: true
        circulatingSupply:
          type: string
          nullable: true
        metaplex:
          $ref: '#/components/schemas/Metaplex'
        links:
          type: object
          nullable: true
        description:
          type: string
          nullable: true
        isVerifiedContract:
          type: boolean
          nullable: true
        possibleSpam:
          type: boolean
      required:
        - mint
        - standard
        - name
        - symbol
        - logo
        - decimals
        - tokenStandard
        - score
        - totalSupply
        - totalSupplyFormatted
        - fullyDilutedValue
        - marketCap
        - circulatingSupply
        - metaplex
        - links
        - description
        - isVerifiedContract
        - possibleSpam
    Metaplex:
      type: object
      properties:
        metadataUri:
          type: string
          nullable: true
        masterEdition:
          type: boolean
        isMutable:
          type: boolean
        primarySaleHappened:
          type: number
        sellerFeeBasisPoints:
          type: number
        updateAuthority:
          type: string
          nullable: true
      required:
        - metadataUri
        - masterEdition
        - isMutable
        - primarySaleHappened
        - sellerFeeBasisPoints
        - updateAuthority
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````