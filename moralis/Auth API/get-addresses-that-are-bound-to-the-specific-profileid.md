> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Get addresses that are bound to the specific profileId



## OpenAPI

````yaml /openapi-files/auth-api/auth.json get /profile/{profileId}/addresses
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
  /profile/{profileId}/addresses:
    get:
      tags:
        - Profile
      summary: Get addresses that are bound to the specific profileId
      operationId: getAddresses
      parameters:
        - name: profileId
          required: true
          in: path
          description: Unique identifier with a length of 66 characters
          example: '0xbfbcfab169c67072ff418133124480fea02175f1402aaa497daa4fd09026b0e1'
          schema:
            type: string
      responses:
        '201':
          description: The addresses that are bound to the speicifc profileId
          content:
            application/json:
              schema:
                type: array
                items:
                  type: string
      security:
        - ApiKeyAuth: []
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

````