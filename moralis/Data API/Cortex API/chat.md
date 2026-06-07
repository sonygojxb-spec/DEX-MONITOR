> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Chat

<Warning>
  **Deprecated — scheduled for removal on June 4, 2026.** The Cortex API is being retired. Migrate to [Onchain Skills](/data-api/onchain-skills/overview). See the [changelog](/changelog) for details.
</Warning>


## OpenAPI

````yaml /openapi-files/data-api/cortex.json POST /chat
openapi: 3.0.0
info:
  title: Moralis Cortex API
  description: API Documentation
  contact: {}
  version: 0.0.1
servers: []
security: []
tags: []
paths:
  /chat:
    post:
      tags:
        - Mcp
      operationId: McpController_chat
      parameters: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PromptDto'
      responses:
        '200':
          description: When `stream` is `false`
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PromptResponseDto'
        default:
          description: When `stream` is `true`
          content:
            text/event-stream: {}
      deprecated: true
      security:
        - ApiKeyAuth: []
components:
  schemas:
    PromptDto:
      type: object
      properties:
        prompt:
          type: string
          example: >-
            Provide a detailed analysis of PEPE holders, is the trend bullish or
            bearish?
        model:
          type: string
          description: Select model
          enum:
            - gpt-4.1-mini
            - gpt-4.1-nano
          example: gpt-4.1-mini
        stream:
          type: boolean
          description: Stream over SSE
          example: false
      required:
        - prompt
    PromptResponseDto:
      type: object
      properties:
        text:
          type: string
      required:
        - text
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

````