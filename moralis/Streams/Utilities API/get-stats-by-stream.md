> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Get Stats by Stream

> Get the stats for the streamId specified



## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml GET /stats/{streamId}
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
  /stats/{streamId}:
    get:
      tags:
        - Stats
      summary: Get project stats by Stream ID
      description: Get the stats for the streamId specified
      operationId: GetStatsByStreamId
      parameters:
        - description: The id of the stream to get the stats
          in: path
          name: streamId
          required: true
          schema:
            $ref: '#/components/schemas/UUID'
      responses:
        '200':
          description: Ok
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UsageStatsModel'
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
    UsageStatsModel:
      properties:
        totalWebhooksDelivered:
          type: number
          format: double
          description: The total amount of webhooks delivered across all streams
        totalWebhooksFailed:
          type: number
          format: double
          description: The total amount of failed webhooks across all streams
        totalLogsProcessed:
          type: number
          format: double
          description: >-
            The total amount of logs processed across all streams, this includes
            failed webhooks
        totalTxsProcessed:
          type: number
          format: double
          description: >-
            The total amount of txs processed across all streams, this includes
            failed webhooks
        totalTxsInternalProcessed:
          type: number
          format: double
          description: >-
            The total amount of internal txs processed across all streams, this
            includes failed webhooks
        streams:
          items:
            $ref: '#/components/schemas/UsageStatsStreams'
          type: array
          description: Array of stream stats
        createdAt:
          type: string
          format: date-time
          description: The date since this stats are being counted
        updatedAt:
          type: string
          format: date-time
          description: The date since this stats were last updated
      required:
        - totalWebhooksDelivered
        - totalWebhooksFailed
        - totalLogsProcessed
        - totalTxsProcessed
        - totalTxsInternalProcessed
      type: object
      additionalProperties: false
    UsageStatsStreams:
      properties:
        totalWebhooksDelivered:
          type: number
          format: double
          description: The total amount of webhooks delivered across all streams
        totalWebhooksFailed:
          type: number
          format: double
          description: The total amount of failed webhooks across all streams
        totalLogsProcessed:
          type: number
          format: double
          description: >-
            The total amount of logs processed across all streams, this includes
            failed webhooks
        totalTxsProcessed:
          type: number
          format: double
          description: >-
            The total amount of txs processed across all streams, this includes
            failed webhooks
        totalTxsInternalProcessed:
          type: number
          format: double
          description: >-
            The total amount of internal txs processed across all streams, this
            includes failed webhooks
        streamId:
          type: string
          description: The stream id
      required:
        - totalWebhooksDelivered
        - totalWebhooksFailed
        - totalLogsProcessed
        - totalTxsProcessed
        - totalTxsInternalProcessed
        - streamId
      type: object
      additionalProperties: false
  securitySchemes:
    x-api-key:
      type: apiKey
      name: x-api-key
      in: header

````