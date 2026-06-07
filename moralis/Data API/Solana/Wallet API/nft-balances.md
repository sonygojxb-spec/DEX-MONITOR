> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# NFT Balances

> Gets NFTs owned by the given address

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

<EndpointMeta cus={10} />


## OpenAPI

````yaml /openapi-files/data-api/solana-api.json GET /account/{network}/{address}/nft
openapi: 3.0.0
info:
  title: Moralis Solana API
  version: '1.0'
servers:
  - url: https://solana-gateway.moralis.io
security: []
paths:
  /account/{network}/{address}/nft:
    get:
      tags:
        - Account
      summary: Gets NFTs owned by the given address
      description: Gets NFTs owned by the given address
      operationId: getNFTs
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
        - name: nftMetadata
          required: false
          in: query
          description: Should return the full NFT metadata
          schema:
            default: false
            type: boolean
        - name: mediaItems
          required: false
          in: query
          description: Should return media items
          schema:
            default: false
            type: boolean
        - name: excludeSpam
          required: false
          in: query
          description: Should exclude spam NFTs
          schema:
            default: false
            type: boolean
        - name: includeFungibleAssets
          required: false
          in: query
          description: Should include fungible assets (tokenStandard:1)
          schema:
            default: false
            type: boolean
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/SPLNFT'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    SPLNFT:
      type: object
      properties:
        associatedTokenAddress:
          type: string
        mint:
          type: string
        name:
          type: string
        symbol:
          type: string
        tokenStandard:
          type: number
          nullable: true
        amount:
          type: string
        amountRaw:
          type: string
        decimals:
          type: number
        possibleSpam:
          type: boolean
        totalSupply:
          type: string
        attributes:
          type: array
          items:
            $ref: '#/components/schemas/NFTMetadataAttributeDto'
        contract:
          $ref: '#/components/schemas/NFTMetadataContractDto'
        collection:
          $ref: '#/components/schemas/NFTMetadataCollectionDto'
        firstCreated:
          $ref: '#/components/schemas/NFTMetadataFirstCreatedDto'
        creators:
          nullable: true
          type: array
          items:
            $ref: '#/components/schemas/NFTMetadataCreatorDto'
        properties:
          type: object
          nullable: true
        media:
          nullable: true
          allOf:
            - $ref: '#/components/schemas/Media'
      required:
        - associatedTokenAddress
        - mint
        - name
        - symbol
        - tokenStandard
        - amount
        - amountRaw
        - decimals
        - possibleSpam
    NFTMetadataAttributeDto:
      type: object
      properties:
        traitType:
          type: string
          nullable: true
        value:
          type: object
      required:
        - traitType
        - value
    NFTMetadataContractDto:
      type: object
      properties:
        type:
          type: string
          nullable: true
        name:
          type: string
          nullable: true
        symbol:
          type: string
          nullable: true
      required:
        - type
        - name
        - symbol
    NFTMetadataCollectionDto:
      type: object
      properties:
        collectionAddress:
          type: string
          nullable: true
        name:
          type: string
          nullable: true
        description:
          type: string
          nullable: true
        imageOriginalUrl:
          type: string
          nullable: true
        externalUrl:
          type: string
          nullable: true
        metaplexMint:
          type: string
          nullable: true
        sellerFeeBasisPoints:
          type: number
          nullable: true
      required:
        - collectionAddress
        - name
        - description
        - imageOriginalUrl
        - externalUrl
        - metaplexMint
        - sellerFeeBasisPoints
    NFTMetadataFirstCreatedDto:
      type: object
      properties:
        mintTimestamp:
          type: number
          nullable: true
        mintBlockNumber:
          type: number
          nullable: true
        mintTransaction:
          type: string
          nullable: true
      required:
        - mintTimestamp
        - mintBlockNumber
        - mintTransaction
    NFTMetadataCreatorDto:
      type: object
      properties:
        address:
          type: string
          nullable: true
        share:
          type: number
          nullable: true
        verified:
          type: boolean
          nullable: true
      required:
        - address
        - share
        - verified
    Media:
      type: object
      properties:
        mimetype:
          type: string
        category:
          type: string
        originalMediaUrl:
          type: string
        status:
          type: string
        updatedAt:
          type: string
        mediaCollection:
          $ref: '#/components/schemas/MediaCollection'
    MediaCollection:
      type: object
      properties:
        low:
          $ref: '#/components/schemas/MediaItem'
        medium:
          $ref: '#/components/schemas/MediaItem'
        high:
          $ref: '#/components/schemas/MediaItem'
    MediaItem:
      type: object
      properties:
        width:
          type: number
        height:
          type: number
        url:
          type: string
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key

````