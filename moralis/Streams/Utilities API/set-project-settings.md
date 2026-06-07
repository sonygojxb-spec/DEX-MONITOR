> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Set Project Settings

> Set the settings for the current project based on the project api-key.



## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml POST /settings
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
  /settings:
    post:
      tags:
        - Project
      summary: Set project settings
      description: Set the settings for the current project based on the project api-key.
      operationId: SetSettings
      parameters: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SettingsModel'
      responses:
        '200':
          description: Ok
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SettingsModel'
      security:
        - x-api-key: []
components:
  schemas:
    SettingsModel:
      properties:
        region:
          $ref: '#/components/schemas/SettingsRegion'
          description: >-
            The region from where all the webhooks will be posted for this
            project
        secretKey:
          type: string
          description: The secret key to validate the webhooks
      type: object
      additionalProperties: false
    SettingsRegion:
      enum:
        - us-east-1
        - us-west-2
        - eu-central-1
        - ap-southeast-1
      type: string
  securitySchemes:
    x-api-key:
      type: apiKey
      name: x-api-key
      in: header

````