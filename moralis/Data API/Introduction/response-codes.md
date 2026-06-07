> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Response Codes

> Moralis uses conventional HTTP response codes to indicate success or failure of an API request.

| Status Code | Message               | Description                                                                    |
| ----------- | --------------------- | ------------------------------------------------------------------------------ |
| 200         | OK                    | Everything worked as expected.                                                 |
| 201         | Created               | Resource has been successfully created or added to a queue.                    |
| 202         | Accepted              | Resource has been successfully created or added to a queue.                    |
| 400         | Bad Request           | Bad request, often due to missing or malformed parameter(s).                   |
| 401         | Unauthorized          | Missing or invalid API key.                                                    |
| 404         | Not Found             | Resource not found (for example pair or token not found for a specific chain). |
| 429         | Rate Limited          | Too many requests. Consider upgrading your plan.                               |
| 500         | Internal Server Error | Something went wrong on Moralis' end.                                          |
