> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Get History

> Get all history



## OpenAPI

````yaml /openapi-files/streams-api/streams.yaml GET /history
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
  /history:
    get:
      tags:
        - History
      summary: Get history
      description: Get all history
      operationId: GetHistory
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
          name: transactionHash
          required: false
          schema:
            type: string
        - in: query
          name: excludePayload
          required: false
          schema:
            type: boolean
        - in: query
          name: streamId
          required: false
          schema:
            type: string
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
                $ref: '#/components/schemas/HistoryResponse'
      security:
        - x-api-key: []
components:
  schemas:
    HistoryResponse:
      properties:
        result:
          items:
            $ref: '#/components/schemas/HistoryModel'
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
    HistoryModel:
      properties:
        id:
          $ref: '#/components/schemas/UUID'
        date:
          type: string
          format: date-time
        payload:
          $ref: '#/components/schemas/IWebhookUnParsed'
        tinyPayload:
          $ref: '#/components/schemas/ITinyPayload'
        errorMessage:
          type: string
        webhookUrl:
          type: string
        streamId:
          type: string
        tag:
          type: string
      required:
        - id
        - date
        - tinyPayload
        - errorMessage
        - webhookUrl
        - streamId
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
    IWebhookUnParsed:
      properties:
        block:
          $ref: '#/components/schemas/Block'
        chainId:
          type: string
        logs:
          items:
            $ref: '#/components/schemas/Log'
          type: array
        txs:
          items:
            $ref: '#/components/schemas/Transaction'
          type: array
        txsInternal:
          items:
            $ref: '#/components/schemas/InternalTransaction'
          type: array
        abi:
          items:
            $ref: '#/components/schemas/AbiItem'
          type: array
        retries:
          type: number
          format: double
        confirmed:
          type: boolean
        tag:
          type: string
        streamId:
          type: string
      required:
        - block
        - chainId
        - logs
        - txs
        - txsInternal
        - abi
        - retries
        - confirmed
        - tag
        - streamId
      type: object
      additionalProperties: false
    ITinyPayload:
      properties:
        chainId:
          type: string
        confirmed:
          type: boolean
        block:
          type: string
        records:
          type: number
          format: double
        retries:
          type: number
          format: double
      required:
        - chainId
        - confirmed
        - block
        - records
        - retries
      type: object
      additionalProperties: false
    Block:
      properties:
        number:
          type: string
        hash:
          type: string
        timestamp:
          type: string
      required:
        - number
        - hash
        - timestamp
      type: object
      additionalProperties: false
    Log:
      properties:
        triggers:
          items:
            $ref: '#/components/schemas/TriggerOutput'
          type: array
        logIndex:
          type: string
        transactionHash:
          type: string
        address:
          type: string
        data:
          type: string
        topic0:
          type: string
          nullable: true
        topic1:
          type: string
          nullable: true
        topic2:
          type: string
          nullable: true
        topic3:
          type: string
          nullable: true
        triggered_by:
          items:
            type: string
          type: array
          nullable: true
      required:
        - logIndex
        - transactionHash
        - address
        - data
        - topic0
        - topic1
        - topic2
        - topic3
      type: object
      additionalProperties: false
    Transaction:
      properties:
        triggers:
          items:
            $ref: '#/components/schemas/TriggerOutput'
          type: array
        hash:
          type: string
        gas:
          type: string
          nullable: true
        gasPrice:
          type: string
          nullable: true
        nonce:
          type: string
          nullable: true
        input:
          type: string
          nullable: true
        transactionIndex:
          type: string
        fromAddress:
          type: string
        toAddress:
          type: string
          nullable: true
        value:
          type: string
          nullable: true
        type:
          type: string
          nullable: true
        v:
          type: string
          nullable: true
        r:
          type: string
          nullable: true
        s:
          type: string
          nullable: true
        receiptCumulativeGasUsed:
          type: string
          nullable: true
        receiptGasUsed:
          type: string
          nullable: true
        receiptContractAddress:
          type: string
          nullable: true
        receiptRoot:
          type: string
          nullable: true
        receiptStatus:
          type: string
          nullable: true
        triggered_by:
          items:
            type: string
          type: array
          nullable: true
        transactionFee:
          type: string
          nullable: true
      required:
        - hash
        - gas
        - gasPrice
        - nonce
        - input
        - transactionIndex
        - fromAddress
        - toAddress
        - value
        - type
        - v
        - r
        - s
        - receiptCumulativeGasUsed
        - receiptGasUsed
        - receiptContractAddress
        - receiptRoot
        - receiptStatus
      type: object
      additionalProperties: false
    InternalTransaction:
      properties:
        from:
          type: string
          nullable: true
        to:
          type: string
          nullable: true
        value:
          type: string
          nullable: true
        transactionHash:
          type: string
        gas:
          type: string
          nullable: true
        triggered_by:
          items:
            type: string
          type: array
          nullable: true
      required:
        - from
        - to
        - value
        - transactionHash
        - gas
      type: object
      additionalProperties: false
    AbiItem:
      description: The abi to parse the log object of the contract
      properties:
        anonymous:
          type: boolean
        constant:
          type: boolean
        inputs:
          items:
            $ref: '#/components/schemas/AbiInput'
          type: array
        name:
          type: string
        outputs:
          items:
            $ref: '#/components/schemas/AbiOutput'
          type: array
        payable:
          type: boolean
        stateMutability:
          type: string
        type:
          type: string
        gas:
          type: number
          format: double
      required:
        - type
      type: object
      additionalProperties: false
      example: {}
    TriggerOutput:
      properties:
        value: {}
        name:
          type: string
      required:
        - value
        - name
      type: object
    AbiInput:
      properties:
        name:
          type: string
        type:
          type: string
        indexed:
          type: boolean
        components:
          items:
            $ref: '#/components/schemas/AbiInput'
          type: array
        internalType:
          type: string
      required:
        - name
        - type
      type: object
      additionalProperties: false
    AbiOutput:
      properties:
        name:
          type: string
        type:
          type: string
        components:
          items:
            $ref: '#/components/schemas/AbiOutput'
          type: array
        internalType:
          type: string
      required:
        - name
        - type
      type: object
      additionalProperties: false
  securitySchemes:
    x-api-key:
      type: apiKey
      name: x-api-key
      in: header

````