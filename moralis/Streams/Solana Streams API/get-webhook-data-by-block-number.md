> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Get Webhook Data by Block Number



## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml POST /streams/solana/{chainId}/block/{blockNumber}
openapi: 3.0.0
info:
  title: Streams Api
  version: 1.0.0
  description: API that provides access to Moralis Streams
  contact: {}
servers:
  - url: https://api.moralis-streams.com
security: []
paths:
  /streams/solana/{chainId}/block/{blockNumber}:
    post:
      tags:
        - Solana Streams
      operationId: solanaGetBlockByNumber
      parameters:
        - in: path
          name: chainId
          required: true
          schema:
            type: string
        - in: path
          name: blockNumber
          required: true
          schema:
            type: number
            format: double
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SolanaBlockDataByNumber'
      responses:
        '200':
          description: Ok
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/SolanaWebhook'
                nullable: true
      security:
        - x-api-key: []
components:
  schemas:
    SolanaBlockDataByNumber:
      properties:
        tag:
          type: string
          description: A user-provided tag that will be send along the webhook
        allAddresses:
          type: boolean
          description: Include events for all addresses
        addresses:
          items:
            type: string
          type: array
          description: Solana addresses to filter by
        programIds:
          items:
            type: string
          type: array
          description: Solana program IDs to filter by
        mintAddresses:
          items:
            type: string
          type: array
          description: Solana token mint addresses to filter by
      type: object
      additionalProperties: false
    SolanaWebhook:
      properties:
        block:
          $ref: '#/components/schemas/SolanaBlockInfo'
        chainId:
          type: string
        network:
          type: string
          enum:
            - mainnet
            - devnet
        retries:
          type: number
          format: double
        streamId:
          type: string
        tag:
          type: string
        transactions:
          items:
            $ref: '#/components/schemas/SolanaTransactionWebhook'
          type: array
        confirmed:
          type: boolean
      required:
        - block
        - chainId
        - network
        - retries
        - streamId
        - tag
        - transactions
        - confirmed
      type: object
      additionalProperties: false
    SolanaBlockInfo:
      properties:
        previousBlockHash:
          type: string
        parentSlot:
          type: string
        blockTime:
          type: number
          format: double
          nullable: true
        blockHeight:
          type: string
          nullable: true
        blockHash:
          type: string
        slot:
          type: string
      required:
        - previousBlockHash
        - parentSlot
        - blockTime
        - blockHeight
        - blockHash
        - slot
      type: object
    SolanaTransactionWebhook:
      properties:
        postTokenBalances:
          items: {}
          type: array
          nullable: true
        preTokenBalances:
          items: {}
          type: array
          nullable: true
        innerInstructions:
          items: {}
          type: array
          nullable: true
        instructions:
          items:
            $ref: '#/components/schemas/SolanaInstructionWebhook'
          type: array
        accountKeys:
          items:
            type: string
          type: array
        err:
          nullable: true
        fee:
          type: string
        blockTime:
          type: number
          format: double
          nullable: true
        slot:
          type: string
        signature:
          type: string
      required:
        - postTokenBalances
        - preTokenBalances
        - innerInstructions
        - instructions
        - accountKeys
        - err
        - fee
        - blockTime
        - slot
        - signature
      type: object
    SolanaInstructionWebhook:
      properties:
        accounts:
          items:
            type: string
          type: array
          nullable: true
        data:
          type: string
          nullable: true
        programId:
          type: string
      required:
        - accounts
        - data
        - programId
      type: object
  securitySchemes:
    x-api-key:
      type: apiKey
      name: x-api-key
      in: header

````