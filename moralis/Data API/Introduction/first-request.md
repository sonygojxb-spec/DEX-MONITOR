> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Make Your First Request

> Learn how to get started with the Moralis Data API.

### Your first request

Let's make your first request using the [Wallet API](/data-api/evm/wallet/overview).\
In this example, we'll retrieve **token balances** for a wallet on Ethereum - including **formatted balances, USD values, prices, and metadata** - with a single API call using [Token Balances](/data-api/evm/wallet/token-balances).

### What we'll fetch

* All ERC-20 and native token balances for a wallet
* Enriched data such as token metadata, prices, and USD values
* Normalized output you can use directly in apps or dashboards

### Make the request

```bash cURL theme={null}
curl --request GET \
  --url 'https://deep-index.moralis.io/api/v2.2/wallets/0xcB1C1FdE09f811B294172696404e88E658659905/tokens?chain=eth' \
  --header 'X-API-Key: YOUR_API_KEY'
```

<Info>
  Replace `YOUR_API_KEY` with the API key from your [Moralis dashboard](/data-api/get-your-api-key).
</Info>

### Response

The API returns a JSON object containing the wallet's token balances. Each entry includes balances, prices, USD values, and security metadata.

```json Response (JSON) expandable theme={null}
{
    "cursor": null,
    "page": 0,
    "page_size": 100,
    "block_number": 23998783,
    "result": [
        {
            "token_address": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            "symbol": "ETH",
            "name": "Ether",
            "logo": "https://cdn.moralis.io/eth/0x.png",
            "thumbnail": "https://cdn.moralis.io/eth/0x_thumb.png",
            "decimals": 18,
            "balance": "1709495362615127",
            "possible_spam": false,
            "verified_contract": true,
            "total_supply": null,
            "total_supply_formatted": null,
            "percentage_relative_to_total_supply": null,
            "security_score": 99,
            "balance_formatted": "0.001709495362615127",
            "usd_price": 3074.275584969874,
            "usd_price_24hr_percent_change": -4.046936070446101,
            "usd_price_24hr_usd_change": -129.54660056550028,
            "usd_value": 5.255459855906907,
            "usd_value_24hr_usd_change": -0.22145931290927692,
            "native_token": true,
            "portfolio_percentage": 57.264259068625606
        },
        {
            "token_address": "0x4fabb145d64652a948d72533023f6e7a623c7c53",
            "symbol": "BUSD",
            "name": "BUSD",
            "logo": "https://logo.moralis.io/0x1_0x4fabb145d64652a948d72533023f6e7a623c7c53_05b49a8d713a42d99fc194279df539e7.png",
            "thumbnail": "https://logo.moralis.io/0x1_0x4fabb145d64652a948d72533023f6e7a623c7c53_05b49a8d713a42d99fc194279df539e7.png",
            "decimals": 18,
            "balance": "2102143890000000000",
            "possible_spam": false,
            "verified_contract": true,
            "total_supply": "55026240205945520000000000",
            "total_supply_formatted": "55026240.20594552",
            "percentage_relative_to_total_supply": 0.000003820257175726,
            "security_score": 76,
            "balance_formatted": "2.10214389",
            "usd_price": 0.9966474180866458,
            "usd_price_24hr_percent_change": -0.33116797769114314,
            "usd_price_24hr_usd_change": -0.0033115438720600077,
            "usd_value": 2.0950962804151176,
            "usd_value_24hr_usd_change": -0.006961341717117886,
            "native_token": false,
            "portfolio_percentage": 22.82847542647662
        },
		{},
		{}
	]
}
```

### What you get

With a single request, Moralis provides:

* **Low-latency access** to onchain wallet data
* **Normalized balances** across tokens
* **Enriched pricing and USD values**
* **Token metadata and security signals**
* Production-ready responses for apps and analytics

No RPC calls, no custom indexing, no manual price joins.

### Next steps

* Explore more endpoints in the **Wallet API**
* Fetch **NFT balances** or **transaction history**
* Combine with **Streams** to react to wallet activity in real time
* Use **Datashare** or **Data Feeds** for large-scale analytics
