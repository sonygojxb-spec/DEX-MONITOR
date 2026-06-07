> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Get Logs

> Get All logs.



## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml GET /history/logs
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
  /history/logs:
    get:
      tags:
        - History
      summary: Get logs
      description: Get All logs.
      operationId: GetLogs
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
        - in: query
          name: streamId
          required: false
          schema:
            type: string
        - in: query
          name: transactionHash
          required: false
          schema:
            type: string
        - in: query
          name: deliveryStatus
          required: false
          schema:
            items:
              type: string
            type: array
        - in: query
          name: chainId
          required: false
          schema:
            items:
              type: string
            type: array
        - in: query
          name: blockNumber
          required: false
          schema:
            type: array
            items:
              type: number
              format: double
        - in: query
          name: fromTimestamp
          required: false
          schema:
            type: number
            format: double
        - in: query
          name: toTimestamp
          required: false
          schema:
            type: number
            format: double
      responses:
        '200':
          description: Ok
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/IWebhookDeliveryLogsResponse'
      security:
        - x-api-key: []
components:
  schemas:
    IWebhookDeliveryLogsResponse:
      properties:
        result:
          items:
            $ref: '#/components/schemas/IWebhookDeliveryLogsModel'
          type: array
        cursor:
          type: string
        total:
          type: number
          format: double
      required:
        - result
        - total
      type: object
      additionalProperties: false
    IWebhookDeliveryLogsModel:
      properties:
        id:
          $ref: '#/components/schemas/UUID'
        streamId:
          type: string
        chain:
          type: string
        webhookUrl:
          type: string
        tag:
          type: string
        retries:
          type: number
          format: double
        deliveryStatus:
          type: string
          enum:
            - failed
            - success
        blockNumber:
          type: number
          format: double
        errorMessage:
          type: string
        type:
          type: string
          enum:
            - evm
            - aptos
            - bitcoin
        createdAt:
          type: string
          format: date-time
      required:
        - id
        - streamId
        - chain
        - webhookUrl
        - retries
        - deliveryStatus
        - blockNumber
        - errorMessage
        - type
        - createdAt
      type: object
      additionalProperties: false
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