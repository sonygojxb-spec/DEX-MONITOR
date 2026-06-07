> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Update Stream Status



## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml POST /streams/solana/{id}/status
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
  /streams/solana/{id}/status:
    post:
      tags:
        - Solana Streams
      operationId: solanaStreamsUpdateStatus
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
              $ref: '#/components/schemas/StreamsStatusUpdate'
      responses:
        '200':
          description: Ok
          content:
            application/json:
              schema:
                $ref: >-
                  #/components/schemas/Pick_SolanaStreamType.status-or-statusMessage_
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
    StreamsStatusUpdate:
      properties:
        status:
          $ref: '#/components/schemas/StreamsStatus'
          description: The status of the stream.
      required:
        - status
      type: object
      additionalProperties: false
    Pick_SolanaStreamType.status-or-statusMessage_:
      properties:
        status:
          $ref: '#/components/schemas/StreamsStatus'
        statusMessage:
          type: string
      required:
        - status
        - statusMessage
      type: object
      description: From T, pick a set of properties whose keys are in the union K
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