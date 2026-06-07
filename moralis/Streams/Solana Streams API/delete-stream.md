> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Delete Stream



## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml DELETE /streams/solana/{id}
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
    delete:
      tags:
        - Solana Streams
      operationId: solanaStreamsDelete
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Ok
          content:
            application/json:
              schema:
                type: boolean
      security:
        - x-api-key: []
components:
  securitySchemes:
    x-api-key:
      type: apiKey
      name: x-api-key
      in: header

````