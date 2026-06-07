> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Data API Supported Chains

> Blockchains supported by the Moralis Data APIs for tokens, wallets, NFTs, DeFi, and pricing.

export const DataApiSupportedChainsTable = () => {
  const features = [{
    key: "all",
    label: "All Features"
  }, {
    key: "dataApi",
    label: "Data API"
  }, {
    key: "wallet",
    label: "Wallet"
  }, {
    key: "nft",
    label: "NFT"
  }, {
    key: "token",
    label: "Token"
  }, {
    key: "defi",
    label: "DeFi"
  }, {
    key: "entity",
    label: "Entity"
  }, {
    key: "blockchain",
    label: "Blockchain"
  }, {
    key: "pnl",
    label: "PNL"
  }, {
    key: "prices",
    label: "Prices"
  }, {
    key: "internalTxs",
    label: "Internal Txs"
  }, {
    key: "nftTrades",
    label: "NFT Trades"
  }, {
    key: "nftPrices",
    label: "NFT Prices"
  }, {
    key: "floorPrices",
    label: "Floor Prices"
  }];
  const mk = (...vals) => {
    const keys = features.slice(1).map(f => f.key);
    const obj = {};
    keys.forEach((k, i) => obj[k] = vals[i]);
    return obj;
  };
  const T = true;
  const F = false;
  const chains = [{
    name: "Ethereum Mainnet",
    type: "Mainnet",
    chainId: "0x1 (1)",
    qp: ["eth", "0x1"],
    s: mk(T, T, T, T, T, T, T, T, T, T, T, T, T)
  }, {
    name: "Ethereum Sepolia",
    type: "Testnet",
    chainId: "0xaa36a7 (11155111)",
    qp: ["sepolia", "0xaa36a7"],
    s: mk(T, T, T, T, F, T, T, F, F, T, F, F, F)
  }, {
    name: "Polygon Mainnet",
    type: "Mainnet",
    chainId: "0x89 (137)",
    qp: ["polygon", "0x89"],
    s: mk(T, T, T, T, T, T, T, T, T, T, T, T, T)
  }, {
    name: "Polygon Amoy",
    type: "Testnet",
    chainId: "0x13882 (80002)",
    qp: ["polygon amoy", "0x13882"],
    s: mk(T, T, T, T, F, T, T, F, F, T, F, F, F)
  }, {
    name: "Binance Smart Chain Mainnet",
    type: "Mainnet",
    chainId: "0x38 (56)",
    qp: ["bsc", "0x38"],
    s: mk(T, T, T, T, T, T, T, F, T, T, T, T, T)
  }, {
    name: "Binance Smart Chain Testnet",
    type: "Testnet",
    chainId: "0x61 (97)",
    qp: ["bsc testnet", "0x61"],
    s: mk(T, T, T, T, F, T, T, F, F, T, F, F, F)
  }, {
    name: "Arbitrum",
    type: "Mainnet",
    chainId: "0xa4b1 (42161)",
    qp: ["arbitrum", "0xa4b1"],
    s: mk(T, T, T, T, T, T, T, F, T, T, T, T, T)
  }, {
    name: "Base",
    type: "Mainnet",
    chainId: "0x2105 (8453)",
    qp: ["base", "0x2105"],
    s: mk(T, T, T, T, T, T, T, T, T, T, T, T, T)
  }, {
    name: "Base Sepolia",
    type: "Testnet",
    chainId: "0x14a34 (84532)",
    qp: ["base sepolia", "0x14a34"],
    s: mk(T, T, T, T, F, T, T, F, F, T, F, F, F)
  }, {
    name: "Optimism",
    type: "Mainnet",
    chainId: "0xa (10)",
    qp: ["optimism", "0xa"],
    s: mk(T, T, T, T, T, T, T, F, T, T, T, T, T)
  }, {
    name: "Linea",
    type: "Mainnet",
    chainId: "0xe708 (59144)",
    qp: ["linea", "0xe708"],
    s: mk(T, T, T, T, T, T, T, F, T, T, F, F, F)
  }, {
    name: "Linea Sepolia",
    type: "Testnet",
    chainId: "0xe705 (59141)",
    qp: ["linea sepolia", "0xe705"],
    s: mk(T, T, T, T, F, T, T, F, F, T, F, F, F)
  }, {
    name: "Avalanche",
    type: "Mainnet",
    chainId: "0xa86a (43114)",
    qp: ["avalanche", "0xa86a"],
    s: mk(T, T, T, T, T, T, T, F, T, T, T, T, T)
  }, {
    name: "Fantom Mainnet",
    type: "Mainnet",
    chainId: "0xfa (250)",
    qp: ["fantom", "0xfa"],
    s: mk(T, T, T, T, F, T, T, F, T, T, F, F, F)
  }, {
    name: "Cronos Mainnet",
    type: "Mainnet",
    chainId: "0x19 (25)",
    qp: ["cronos", "0x19"],
    s: mk(T, T, T, T, F, T, T, F, T, F, F, F, F)
  }, {
    name: "Gnosis",
    type: "Mainnet",
    chainId: "0x64 (100)",
    qp: ["gnosis", "0x64"],
    s: mk(T, T, F, T, F, T, T, F, T, T, F, F, F)
  }, {
    name: "Gnosis Chiado",
    type: "Testnet",
    chainId: "0x27d8 (10200)",
    qp: ["gnosis testnet", "0x27d8"],
    s: mk(T, T, F, T, F, T, T, F, F, F, F, F, F)
  }, {
    name: "Chiliz Mainnet",
    type: "Mainnet",
    chainId: "0x15b38 (88888)",
    qp: ["chiliz", "0x15b38"],
    s: mk(T, T, T, T, F, T, T, F, F, T, F, F, F)
  }, {
    name: "Chiliz Testnet",
    type: "Testnet",
    chainId: "0x15b32 (88882)",
    qp: ["chiliz testnet", "0x15b32"],
    s: mk(T, T, T, T, F, T, T, F, F, T, F, F, F)
  }, {
    name: "Moonbeam",
    type: "Mainnet",
    chainId: "0x504 (1284)",
    qp: ["moonbeam", "0x504"],
    s: mk(T, T, T, T, F, T, T, F, F, F, F, F, F)
  }, {
    name: "Moonriver",
    type: "Testnet",
    chainId: "0x505 (1285)",
    qp: ["moonriver", "0x505"],
    s: mk(T, T, T, T, F, T, T, F, F, F, F, F, F)
  }, {
    name: "Moonbase",
    type: "Testnet",
    chainId: "0x507 (1287)",
    qp: ["moonbase", "0x507"],
    s: mk(T, T, T, T, F, T, T, F, F, F, F, F, F)
  }, {
    name: "Flow",
    type: "Mainnet",
    chainId: "0x2eb (747)",
    qp: ["flow", "0x2eb"],
    s: mk(T, T, T, T, F, T, T, F, F, F, F, F, F)
  }, {
    name: "Flow Testnet",
    type: "Testnet",
    chainId: "0x221 (545)",
    qp: ["flow-testnet", "0x221"],
    s: mk(T, T, T, T, F, T, T, F, F, F, F, F, F)
  }, {
    name: "Ronin",
    type: "Mainnet",
    chainId: "0x7e4 (2020)",
    qp: ["ronin", "0x7e4"],
    s: mk(T, T, T, T, F, T, T, F, T, T, T, T, T)
  }, {
    name: "Ronin Saigon Testnet",
    type: "Testnet",
    chainId: "0x7e5 (2021)",
    qp: ["ronin-testnet", "0x31769"],
    s: mk(T, T, T, T, F, T, T, F, F, T, F, F, F)
  }, {
    name: "Lisk",
    type: "Mainnet",
    chainId: "0x46f (1135)",
    qp: ["lisk", "0x46f"],
    s: mk(T, T, T, T, F, T, T, F, F, T, F, F, F)
  }, {
    name: "Lisk Sepolia Testnet",
    type: "Testnet",
    chainId: "0x106a (4202)",
    qp: ["lisk-sepolia", "0x106a"],
    s: mk(T, T, T, T, F, T, T, F, F, T, F, F, F)
  }, {
    name: "Pulsechain",
    type: "Mainnet",
    chainId: "0x171 (369)",
    qp: ["pulse", "0x171"],
    s: mk(T, T, F, T, F, T, T, F, T, T, F, F, F)
  }, {
    name: "Sei",
    type: "Mainnet",
    chainId: "0x531 (1329)",
    qp: ["sei", "0x531"],
    s: mk(T, T, T, T, T, T, T, F, T, T, T, T, T)
  }, {
    name: "Sei Testnet",
    type: "Testnet",
    chainId: "0x530 (1328)",
    qp: ["sei-testnet", "0x530"],
    s: mk(T, T, T, T, T, T, T, F, F, T, F, F, F)
  }, {
    name: "Monad",
    type: "Mainnet",
    chainId: "0x8f (143)",
    qp: ["monad", "0x8f"],
    s: mk(T, T, T, T, T, T, T, F, T, T, T, T, T)
  }, {
    name: "Bitcoin Mainnet",
    type: "Mainnet",
    chainId: "mainnet",
    qp: ["bitcoin", "bitcoin-mainnet"],
    s: mk(T, T, F, T, F, F, T, F, T, F, F, F, F)
  }];
  const [selected, setSelected] = useState("all");
  const visible = selected === "all" ? chains : chains.filter(c => c.s[selected]);
  const Cell = ({on}) => <td style={{
    textAlign: "center"
  }}>
      <span style={{
    color: on ? "#16a34a" : "rgba(128,128,128,0.5)"
  }}>
        {on ? "✓" : "✗"}
      </span>
    </td>;
  const featureCols = features.slice(1);
  return <div>
      <div style={{
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    marginBottom: "16px"
  }}>
        {features.map(f => {
    const active = selected === f.key;
    return <button key={f.key} type="button" onClick={() => setSelected(f.key)} style={{
      padding: "6px 14px",
      fontSize: "14px",
      fontWeight: active ? 600 : 500,
      borderRadius: "9999px",
      cursor: "pointer",
      border: "1px solid",
      borderColor: active ? "#0f7fff" : "rgba(128,128,128,0.4)",
      backgroundColor: active ? "#0f7fff" : "transparent",
      color: active ? "#ffffff" : "inherit"
    }}>
              {f.label}
            </button>;
  })}
      </div>

      <p style={{
    fontSize: "14px",
    marginBottom: "12px",
    opacity: 0.7
  }}>
        Showing <strong>{visible.length}</strong> chain
        {visible.length !== 1 && "s"}
        {selected !== "all" && ` with ${features.find(f => f.key === selected).label} support`}
        .
      </p>

      <table>
        <thead>
          <tr>
            <th>Chain</th>
            <th>Type</th>
            <th>Chain ID</th>
            <th>Query Params</th>
            {featureCols.map(f => <th key={f.key} style={{
    textAlign: "center"
  }}>
                {f.label}
              </th>)}
          </tr>
        </thead>
        <tbody>
          {visible.map(c => <tr key={c.name}>
              <td>{c.name}</td>
              <td>{c.type}</td>
              <td>{c.chainId}</td>
              <td>
                {c.qp.map((p, i) => <span key={p}>
                    {i > 0 && " · "}
                    <code>{p}</code>
                  </span>)}
              </td>
              {featureCols.map(f => <Cell key={f.key} on={c.s[f.key]} />)}
            </tr>)}
        </tbody>
      </table>
    </div>;
};

### Data API Supported Chains

The Moralis Data APIs support multiple blockchain networks for **onchain data access**, including wallets, tokens, NFTs, DeFi, and prices.

Chain support may vary by feature. Some chains support the full Data API surface, while others support a subset depending on:

* Indexing depth
* Protocol availability
* Onchain data structure

Use the selector below to filter the table by feature, or view all features at once.

<DataApiSupportedChainsTable />
