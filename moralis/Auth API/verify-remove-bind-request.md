> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Verify remove bind request



## OpenAPI

````yaml /openapi-files/auth-api/auth.json post /bind/remove/verify
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
  /bind/remove/verify:
    post:
      tags:
        - Bind
      summary: Verify remove bind request
      operationId: verifyRemoveBind
      parameters: []
      requestBody:
        required: true
        description: Messages and its signatures that is used for verification
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BindVerifyRemoveDto'
      responses:
        '201':
          description: The new profileId that is being generated for this address.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BindVerifyRemoveResponseDto'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    BindVerifyRemoveDto:
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
        signature:
          type: string
          description: >-
            EIP-191 compliant signature signed by the Ethereum account address
            requesting authentication.
          example: >-
            0xc4f2f59d80e036ecab4eaaac5d4ee713ab94264ca584839c98b5743c4f6777322038225a4bc1e0f13b8382166816737369f26bd66f0479cfa80d4c52c02eb2cb1b
      required:
        - message
        - signature
    BindVerifyRemoveResponseDto:
      type: object
      properties:
        profileId:
          type: string
          description: Unique identifier with a length of 66 characters
          example: '0xbfbcfab169c67072ff418133124480fea02175f1402aaa497daa4fd09026b0e1'
      required:
        - profileId
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

````