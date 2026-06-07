> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Get Streams



## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml GET /streams/solana
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
  /streams/solana:
    get:
      tags:
        - Solana Streams
      operationId: solanaStreamsGetAll
      parameters:
        - in: query
          name: limit
          required: true
          schema:
            type: number
            format: double
        - in: query
          name: cursor
          required: false
          schema:
            type: string
      responses:
        '200':
          description: Ok
          content:
            application/json:
              schema:
                properties:
                  total:
                    type: number
                    format: double
                  result:
                    items:
                      $ref: '#/components/schemas/SolanaStreamType'
                    type: array
                required:
                  - total
                  - result
                type: object
      security:
        - x-api-key: []
components:
  schemas:
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