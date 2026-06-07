> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Update Stream



## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml POST /streams/solana/{id}
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
  /streams/solana/{id}:
    post:
      tags:
        - Solana Streams
      operationId: solanaStreamsUpdate
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Partial_SolanaCreateStreamType_'
      responses:
        '200':
          description: Ok
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SolanaStreamType'
      security:
        - x-api-key: []
components:
  schemas:
    Partial_SolanaCreateStreamType_:
      properties:
        allAddresses:
          type: boolean
          description: Include events for all addresses
        description:
          type: string
          description: A description for this stream
        network:
          $ref: '#/components/schemas/SolanaNetwork'
          description: The network to listen to
        programIds:
          items:
            type: string
          type: array
          description: Solana program IDs to filter transactions by
        mintAddresses:
          items:
            type: string
          type: array
          description: Solana token mint addresses to filter transactions by
        tag:
          type: string
          description: A user-provided tag that will be send along the webhook
        webhookUrl:
          type: string
          description: Webhook URL where moralis will send the POST request.
      type: object
      description: Make all properties in T optional
    SolanaStreamType:
      properties:
        id:
          type: string
        allAddresses:
          type: boolean
        description:
          type: string
        isErrorSince:
          type: string
          format: date-time
          nullable: true
        network:
          $ref: '#/components/schemas/SolanaNetwork'
        programIds:
          items:
            type: string
          type: array
        mintAddresses:
          items:
            type: string
          type: array
        status:
          $ref: '#/components/schemas/StreamsStatus'
        statusMessage:
          type: string
        tag:
          type: string
        webhookUrl:
          type: string
        amountOfAddresses:
          type: number
          format: double
        updatedAt:
          type: string
          format: date-time
      required:
        - id
        - allAddresses
        - description
        - isErrorSince
        - network
        - programIds
        - mintAddresses
        - status
        - statusMessage
        - tag
        - webhookUrl
        - amountOfAddresses
        - updatedAt
      type: object
      additionalProperties: false
    SolanaNetwork:
      items:
        type: string
        enum:
          - mainnet
          - devnet
      type: array
    StreamsStatus:
      description: |-
        The stream status:
        [active] The Stream is healthy and processing blocks
        [paused] The Stream is paused and is not processing blocks
        [error] The Stream has encountered an error and is not processing blocks
      enum:
        - active
        - paused
        - error
        - terminated
      type: string
      example: {}
  securitySchemes:
    x-api-key:
      type: apiKey
      name: x-api-key
      in: header

````