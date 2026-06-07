> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Verify Solana challenge



## OpenAPI

````yaml /openapi-files/auth-api/auth.json post /challenge/verify/solana
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
  /challenge/verify/solana:
    post:
      tags:
        - Challenge
      summary: Verify Solana challenge
      operationId: verifyChallengeSolana
      parameters: []
      requestBody:
        required: true
        description: Verify Solana challenge message.
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SolanaCompleteChallengeRequestDto'
      responses:
        '201':
          description: The token to be used to call the third party API from the client
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SolanaCompleteChallengeResponseDto'
      security:
        - ApiKeyAuth: []
components:
  schemas:
    SolanaCompleteChallengeRequestDto:
      type: object
      properties:
        message:
          type: string
          description: Message that needs to be signed by the end user
          example: |-
            defi.finance wants you to sign in with your Solana account:
            26qv4GCcx98RihuK3c4T6ozB3J7L6VwCuFVc7Ta2A3Uo

            I am a third party API

            URI: http://defi.finance
            Version: 1
            Network: mainnet
            Nonce: PYxxb9msdjVXsMQ9x
            Issued At: 2022-08-25T11:02:34.097Z
            Expiration Time: 2022-08-25T11:12:38.243Z
            Resources:
            - https://docs.moralis.io/
        signature:
          type: string
          description: Base58 signature that needs to be used to verify end user
          example: >-
            2pH9DqD5rve2qV4yBDshcAjWd2y8TqMx8BPb7f3KoNnuLEhE5JwjruYi4jaFaD4HN6wriLz2Vdr32kRBAJmHcyny
      required:
        - message
        - signature
    SolanaCompleteChallengeResponseDto:
      type: object
      properties:
        id:
          type: string
          maxLength: 64
          minLength: 8
          description: >-
            17-characters Alphanumeric string Secret Challenge ID used to
            identify this particular request. Is should be used at the backend
            of the calling service to identify the completed request.
          example: fRyt67D3eRss3RrX
          pattern: ^[a-zA-Z0-9]{8,64}$
        domain:
          type: string
          description: RFC 4501 dns authority that is requesting the signing.
          example: defi.finance
          format: hostname
        statement:
          type: string
          description: >-
            Human-readable ASCII assertion that the user will sign, and it must
            not contain `

            `.
          example: Please confirm
        uri:
          type: string
          format: uri
          example: https://defi.finance/
          description: >-
            RFC 3986 URI referring to the resource that is the subject of the
            signing (as in the __subject__ of a claim).
        expirationTime:
          type: string
          format: date-time
          example: '2020-01-01T00:00:00.000Z'
          description: >-
            ISO 8601 datetime string that, if present, indicates when the signed
            authentication message is no longer valid.
        notBefore:
          type: string
          format: date-time
          example: '2020-01-01T00:00:00.000Z'
          description: >-
            ISO 8601 datetime string that, if present, indicates when the signed
            authentication message will become valid.
        resources:
          example:
            - https://docs.moralis.io/
          description: >-
            List of information or references to information the user wishes to
            have resolved as part of authentication by the relying party. They
            are expressed as RFC 3986 URIs separated by `

            - `.
          type: array
          items:
            type: string
        version:
          type: string
          example: '1.0'
          description: >-
            EIP-155 Chain ID to which the session is bound, and the network
            where Contract Accounts must be resolved.
        nonce:
          type: string
          example: '0x1234567890abcdef0123456789abcdef1234567890abcdef'
        profileId:
          type: string
          description: Unique identifier with a length of 66 characters
          example: '0xbfbcfab169c67072ff418133124480fea02175f1402aaa497daa4fd09026b0e1'
        network:
          type: string
          enum:
            - mainnet
            - testnet
            - devnet
          example: mainnet
          description: The network where Contract Accounts must be resolved.
        address:
          type: string
          example: 26qv4GCcx98RihuK3c4T6ozB3J7L6VwCuFVc7Ta2A3Uo
          description: >-
            Solana address with a length of 32 - 44 characters that is used to
            perform the signing
      required:
        - id
        - domain
        - uri
        - version
        - nonce
        - profileId
        - network
        - address
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

````