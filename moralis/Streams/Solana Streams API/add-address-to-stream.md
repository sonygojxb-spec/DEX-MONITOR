> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Add Address to Stream

<Warning>
  Solana addresses are base58 and **case-sensitive**. Submit them in their original case — unlike EVM, lowercased addresses will not match.
</Warning>


## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml POST /streams/solana/{id}/address
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
  /streams/solana/{id}/address:
    post:
      tags:
        - Solana Streams
      operationId: solanaStreamsAddAddresses
      parameters:
        - in: path
          name: id
          required: true
          schema:
            $ref: '#/components/schemas/UUID'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              properties:
                address:
                  anyOf:
                    - type: string
                    - items:
                        type: string
                      type: array
              required:
                - address
              type: object
      responses:
        '200':
          description: Ok
          content:
            application/json:
              schema:
                properties:
                  address:
                    anyOf:
                      - type: string
                      - items:
                          type: string
                        type: array
                  streamId:
                    type: string
                required:
                  - address
                  - streamId
                type: object
      security:
        - x-api-key: []
components:
  schemas:
    UUID:
      type: string
      format: uuid
      description: |-
        Stringified UUIDv4.
        See [RFC 4112](https://tools.ietf.org/html/rfc4122)
      pattern: >-
        [0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-4[0-9A-Fa-f]{3}-[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12}
  securitySchemes:
    x-api-key:
      type: apiKey
      name: x-api-key
      in: header

````