> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Request to remove bind of an address from a profile



## OpenAPI

````yaml /openapi-files/auth-api/auth.json post /bind/remove
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
  /bind/remove:
    post:
      tags:
        - Bind
      summary: Request to remove bind of an address from a profile
      operationId: removeBind
      parameters: []
      requestBody:
        required: true
        description: >-
          The address that is required to be removed from the bind of the
          profileId.
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BindRemoveDto'
      responses:
        '201':
          description: The messages that is required to be signed by each of the address
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BindRemoveResponseDto'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    BindRemoveDto:
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
        profileId:
          type: string
          description: Unique identifier with a length of 66 characters
          example: '0xbfbcfab169c67072ff418133124480fea02175f1402aaa497daa4fd09026b0e1'
      required:
        - blockchainType
        - address
        - profileId
    BindRemoveResponseDto:
      type: object
      properties:
        message:
          type: string
          description: Message that needs to be signed by the end user
          example: |-
            Please sign this message to unbind:
            Address: 0x6ed338bcB610640e81465FCfb9894DDfA354Cc91
            from
            Profile Id:
            - 0x0b2bbac1251651c0cbbdbbb29fed5a03adc8b05a2a9eb10a02aaa489b9c1f8ff
            Nonce: 5pXWu7aGkY2J7II0X
      required:
        - message
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

````