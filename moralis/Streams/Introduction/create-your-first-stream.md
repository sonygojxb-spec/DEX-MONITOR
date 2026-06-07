> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Create Your First Stream

> Create a new stream on EVM, Bitcoin, or Solana using the Moralis Admin Panel or the API to start monitoring blockchain addresses and receiving webhook data.

You can create a stream either through the **Moralis Admin Panel** (no code required) or programmatically via the API.

The flow is the same on every chain — define a stream, attach the addresses (or xpub / programs / mints) you care about, and point Moralis at your webhook URL — but the parameters and chain-specific features differ.

<Tabs>
  <Tab title="EVM">
    ## Option 1: Create via Admin Panel

    ### Getting Started

    1. Go to [admin.moralis.com/streams](https://admin.moralis.com/streams).
    2. Click on **Create a new Stream**.
    3. Choose one of the EVM templates:
       * **Custom Event** — Customizable options for events and filters, allowing precise notifications.
       * **Wallet Activity** — Track native transactions and smart contract interactions (transfers, approvals).
       * **Contract Activity** — Monitor smart contract events (logs).

    ### Setting Up the Stream

    1. Name your stream and select the types of events you want to track.
    2. Set up event filtering. See [Filters](/streams/streams-concepts/filters) for details.
    3. Add a tag for your stream and choose if you wish to receive additional data.
    4. Add the addresses you wish to track.
    5. Pick which EVM chains should be tracked (Ethereum, Base, Polygon, etc.).
    6. Test your stream (optional).
    7. Add your webhook URL where the `POST` requests will be sent.

    <Info>For testing, you can use a service like [webhook.site](https://webhook.site/) to receive and inspect webhooks.</Info>

    8. Save your configuration.

    ## Option 2: Create via SDK

    <Info>Make sure you have a Moralis API key. You can get one from the [Moralis Admin Panel](https://admin.moralis.com/).</Info>

    ### Step 1: Create a Stream

    Required parameters:

    * `webhookUrl` — Webhook URL where Moralis will send the `POST` request.
    * `description` — A description for this stream.
    * `tag` — A user-provided tag sent along with the webhook to identify the stream.
    * `chains` — An array of EVM chain IDs to monitor (hex-encoded).
    * At least one of `includeContractLogs`, `includeNativeTxs`, or `includeInternalTxs` must be `true`.

    <Tabs>
      <Tab title="JavaScript">
        ```javascript theme={null}
        const Moralis = require("moralis").default;

        const runApp = async () => {
          await Moralis.start({
            apiKey: "YOUR_API_KEY",
          });

          const response = await Moralis.Streams.add({
            webhookUrl: "https://webhook.site/YOUR_WEBHOOK_URL",
            description: "My first stream",
            tag: "my_stream",
            chains: ["0x1"],
            includeNativeTxs: true,
          });

          console.log(response.toJSON().id); // print the stream id
        };

        runApp();
        ```
      </Tab>

      <Tab title="Python">
        ```python theme={null}
        from moralis import streams

        api_key = "YOUR_API_KEY"

        stream_body = {
            "webhookUrl": "https://webhook.site/YOUR_WEBHOOK_URL",
            "description": "my first stream",
            "tag": "my_stream",
            "chainIds": ["0x1"],
            "includeNativeTxs": True,
        }

        results = streams.evm_streams.create_stream(api_key=api_key, body=stream_body)
        print(results["id"])  # print the stream id
        ```
      </Tab>
    </Tabs>

    ### Step 2: Add an Address to a Stream

    Now that you have a stream ID, you can add addresses to monitor. You can add individual addresses or a batch.

    <Tabs>
      <Tab title="JavaScript">
        ```javascript theme={null}
        const Moralis = require("moralis").default;

        const runApp = async () => {
          await Moralis.start({
            apiKey: "YOUR_API_KEY",
          });

          const list = [
            "0xf3d8d9f1f1ccbc8f7e313b7e7cdaa1d6e5b2c2f2",
            "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
          ];

          const response = await Moralis.Streams.addAddress({
            id: "YOUR_STREAM_ID",
            address: list,
          });

          console.log(response.toJSON());
        };

        runApp();
        ```
      </Tab>

      <Tab title="Python">
        ```python theme={null}
        from moralis import streams

        api_key = "YOUR_API_KEY"

        params = {"id": "YOUR_STREAM_ID"}

        address_list = [
            "0xf3d8d9f1f1ccbc8f7e313b7e7cdaa1d6e5b2c2f2",
            "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
        ]
        stream_body = {"address": address_list}

        results = streams.evm_streams.add_address_to_stream(
            api_key=api_key, body=stream_body, params=params
        )
        print(results)
        ```
      </Tab>
    </Tabs>

    ### Step 3: Update a Stream (Optional)

    You can update a stream to add contract log monitoring, such as listening for ERC-20 transfers.

    <Tabs>
      <Tab title="JavaScript">
        ```javascript theme={null}
        const Moralis = require("moralis").default;

        const runApp = async () => {
          await Moralis.start({
            apiKey: "YOUR_API_KEY",
          });

          const ERC20TransferABI = [
            {
              anonymous: false,
              inputs: [
                { indexed: true, name: "from", type: "address" },
                { indexed: true, name: "to", type: "address" },
                { indexed: false, name: "value", type: "uint256" },
              ],
              name: "Transfer",
              type: "event",
            },
          ];

          const response = await Moralis.Streams.update({
            id: "YOUR_STREAM_ID",
            abi: ERC20TransferABI,
            includeContractLogs: true,
            topic0: ["Transfer(address,address,uint256)"],
            description: "My first stream - with ERC20 transfers",
          });

          console.log(response.toJSON());
        };

        runApp();
        ```
      </Tab>

      <Tab title="Python">
        ```python theme={null}
        from moralis import streams

        api_key = "YOUR_API_KEY"

        erc20_transfer_abi = [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "from", "type": "address"},
                    {"indexed": True, "name": "to", "type": "address"},
                    {"indexed": False, "name": "value", "type": "uint256"},
                ],
                "name": "Transfer",
                "type": "event",
            }
        ]

        params = {"id": "YOUR_STREAM_ID"}

        stream_body = {
            "abi": erc20_transfer_abi,
            "includeContractLogs": True,
            "topic0": ["Transfer(address,address,uint256)"],
            "description": "my first stream - with ERC20 transfers",
        }

        results = streams.evm_streams.update_stream(
            api_key=api_key, body=stream_body, params=params
        )
        print(results)
        ```
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="Bitcoin">
    ## Option 1: Create via Admin Panel

    1. Go to [admin.moralis.com/streams](https://admin.moralis.com/streams).
    2. Click on **Create a new Stream** and choose the **Bitcoin** stream type.
    3. Name your stream, set a tag, and add your webhook URL.
    4. Choose how to monitor wallets:
       * **Individual addresses** — P2PKH (`1...`), P2SH (`3...`), or Bech32 (`bc1q...`)
       * **Xpub** — attach an extended public key and Moralis derives addresses for you
       * **All addresses** — firehose mode that delivers every Bitcoin transaction
    5. Save your configuration.

    See the [Bitcoin Streams overview](/streams/bitcoin-streams) for the full list of features and limitations.

    ## Option 2: Create via API

    <Info>Make sure you have a Moralis API key. You can get one from the [Moralis Admin Panel](https://admin.moralis.com/).</Info>

    ### Step 1: Create a Bitcoin stream

    ```bash theme={null}
    curl -X PUT "https://api.moralis-streams.com/streams/bitcoin" \
      -H "x-api-key: YOUR_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "webhookUrl": "https://webhook.site/YOUR_WEBHOOK_URL",
        "description": "My first Bitcoin stream",
        "tag": "btc_deposits",
        "network": ["mainnet"],
        "includeOutputs": true
      }'
    ```

    Required parameters:

    * `webhookUrl` — public HTTPS endpoint to receive payloads
    * `description` — human-readable stream description
    * `tag` — identifier sent on every webhook for routing on your side
    * `network` — must be `["mainnet"]`

    Optional: `includeInputs`, `includeOutputs`, `allAddresses`. See [Create Bitcoin Stream](/streams/api-reference/bitcoin/streams/create-streams).

    ### Step 2: Add an address (or xpub) to monitor

    Add an individual address:

    ```bash theme={null}
    curl -X POST "https://api.moralis-streams.com/streams/bitcoin/{streamId}/address" \
      -H "x-api-key: YOUR_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{ "address": "bc1qexampleaddressxxxxxxxxxxxxxxxxxxxxxxxx" }'
    ```

    Or attach an xpub so Moralis derives and monitors HD wallet addresses for you:

    ```bash theme={null}
    curl -X POST "https://api.moralis-streams.com/streams/bitcoin/{streamId}/xpub" \
      -H "x-api-key: YOUR_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{ "xpub": "xpub6CUGRUo..." }'
    ```

    See [Add Address](/streams/api-reference/bitcoin/address/add-address-to-stream) and [Add Xpub](/streams/api-reference/bitcoin/xpub/add-xpub) for details.

    <Note>
      Bitcoin Streams delivers each matched transaction **twice** — once at first block inclusion (`confirmed: false`, the block is near the chain tip and could still be reorged) and again after 2 blocks have been mined on top (`confirmed: true`, reorg-safe). Dedupe on `txid` and upsert on the second delivery to flip your local confirmation flag.
    </Note>
  </Tab>

  <Tab title="Solana">
    ## Option 1: Create via Admin Panel

    1. Go to [admin.moralis.com/streams](https://admin.moralis.com/streams).
    2. Click on **Create a new Stream** and choose the **Solana** stream type.
    3. Name your stream, set a tag, and add your webhook URL.
    4. Configure your filters — any combination of:
       * **Addresses** — match transactions where any `accountKey` matches a watched address
       * **Program IDs** — match transactions invoking specific programs (e.g. SPL Token Program)
       * **Mint addresses** — match transactions involving specific SPL tokens
       * **All addresses** — firehose mode for every Solana transaction
    5. Save your configuration.

    See the [Solana Streams overview](/streams/solana-streams) for how Solana concepts (programs, mints, signatures) map from EVM.

    ## Option 2: Create via API

    <Info>Make sure you have a Moralis API key. You can get one from the [Moralis Admin Panel](https://admin.moralis.com/).</Info>

    ### Step 1: Create a Solana stream

    ```bash theme={null}
    curl -X PUT "https://api.moralis-streams.com/streams/solana" \
      -H "x-api-key: YOUR_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "webhookUrl": "https://webhook.site/YOUR_WEBHOOK_URL",
        "description": "My first Solana stream",
        "tag": "sol_wallet_activity",
        "network": ["mainnet"]
      }'
    ```

    Required parameters:

    * `webhookUrl` — public HTTPS endpoint to receive payloads
    * `description` — human-readable stream description
    * `tag` — identifier sent on every webhook for routing on your side
    * `network` — `["mainnet"]`

    See [Create Solana Stream](/streams/api-reference/solana/streams/create-streams) for the full schema.

    ### Step 2: Add addresses, program IDs, or mint addresses

    ```bash theme={null}
    curl -X POST "https://api.moralis-streams.com/streams/solana/{streamId}/address" \
      -H "x-api-key: YOUR_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{ "address": "GoSBxCH19sMnZVEifsXeeMdEfkTv6Zh6MWvQFQF3e5m7" }'
    ```

    <Warning>
      Solana addresses are base58 and **case-sensitive**. Submit them in their original case — unlike EVM, lowercased addresses will not match.
    </Warning>

    See [Add Address](/streams/api-reference/solana/address/add-address-to-stream) for details on attaching addresses, program IDs, and mint addresses.
  </Tab>
</Tabs>

***

## Next Steps

Once your stream is created, you will receive a [mandatory test webhook](/streams/webhooks/test-webhooks) that you must respond to with a `200` status code for the stream to activate.

* [Receive Your First Webhook](/streams/quickstart/receive-your-first-webhook) — Learn what to expect when webhooks start arriving.
* [Webhook Security](/streams/security-and-reliability/webhook-security) — Verify webhook signatures to ensure data authenticity.
* [Filters](/streams/streams-concepts/filters) — Fine-tune which events trigger webhooks.
