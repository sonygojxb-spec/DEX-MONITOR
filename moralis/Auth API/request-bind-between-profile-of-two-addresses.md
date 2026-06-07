> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Request bind between profile of two addresses

> Request for message to bind profile that is belong to the two addresses<br>
        All profiles under the addresses will be bound and new profile will be generated.



## OpenAPI

````yaml /openapi-files/auth-api/auth.json post /bind/request
openapi: 3.0.0
info:
  title: Auth API
  description: API that provides authentication services for dapps.
  version: '1.0'
  contact: {}
servers:
  - url: https://authapi.moralis.io
security: []
tags: []
externalDocs:
  description: View as JSON
  url: ../api-docs-json
paths:
  /bind/request:
    post:
      tags:
        - Bind
      summary: Request bind between profile of two addresses
      description: >-
        Request for message to bind profile that is belong to the two
        addresses<br>
                All profiles under the addresses will be bound and new profile will be generated.
      operationId: requestBind
      parameters: []
      requestBody:
        required: true
        description: The two addresses that are required to be bind.
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BindRequestDto'
      responses:
        '201':
          description: The messages that is required to be signed by each of the address
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BindRequestResponseDto'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    BindRequestDto:
      type: object
      properties:
        addresses:
          description: An array of addresses that needs to be bind
          minItems: 2
          maxItems: 2
          type: array
          items:
            $ref: '#/components/schemas/AddressInfoDto'
      required:
        - addresses
    BindRequestResponseDto:
      type: object
      properties:
        messages:
          description: Message that needs to be signed by the end user
          example:
            - >-
              Please sign this message to bind:

              Profile Ids:

              -
              0x0b2bbac1251651c0cbbdbbb29fed5a03adc8b05a2a9eb10a02aaa489b9c1f8ff


              with


              Address: 0x6ed338bcB610640e81465FCfb9894DDfA354Cc91

              Nonce: 5pXWu7aGkY2J7II0X
            - >-
              Please sign this message to bind:

              Profile Ids:

              -
              0x0b2bbac1251651c0cbbdbbb29fed5a03adc8b05a2a9eb10a02aaa489b9c1f8ff


              with


              Address: 0x6ed338bcB610640e81465FCfb9894DDfA354Cc91

              Nonce: 5pXWu7aGkY2J7II0X
          type: array
          items:
            type: string
      required:
        - messages
    AddressInfoDto:
      type: object
      properties:
        blockchainType:
          type: string
          enum:
            - evm
            - solana
            - aptos
          description: The chain in which the address belongs to
          example: evm
        address:
          type: string
          description: >-
            Address performing the signing conformant to capitalization encoded
            checksum specified in EIP-55 where applicable.
          example: '0x57af6B90c2237d2F888bf4CAe56f25FE1b14e531'
        publicKey:
          type: string
          example: '0xfb2853744bb8afd58d9386d1856afd8e08de135019961dfa3a10d8c9bf83b99d'
          description: >-
            Public key performing the signing conformant. (This is only needed
            for Aptos address)
      required:
        - blockchainType
        - address
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

````