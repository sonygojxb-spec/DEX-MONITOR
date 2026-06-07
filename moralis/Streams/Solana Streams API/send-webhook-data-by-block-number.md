> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Send Webhook Data by Block Number



## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml POST /streams/solana/{chainId}/block-to-webhook/{blockNumber}/{streamId}
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
  /streams/solana/{chainId}/block-to-webhook/{blockNumber}/{streamId}:
    post:
      tags:
        - Solana Streams
      operationId: solanaBlockToWebhook
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
        - in: path
          name: streamId
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Ok
          content:
            application/json:
              schema:
                type: number
                enum:
                  - null
                nullable: true
      security:
        - x-api-key: []
components:
  securitySchemes:
    x-api-key:
      type: apiKey
      name: x-api-key
      in: header

````