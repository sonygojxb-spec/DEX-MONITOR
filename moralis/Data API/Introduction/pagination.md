> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Pagination

> Moralis uses cursor-based pagination for endpoints that return lists (e.g. transactions, transfers, logs, NFTs, etc.).

Pagination lets an API return large result sets in smaller “pages” so responses stay fast and predictable.

Moralis uses **cursor-based pagination** for endpoints that return lists (e.g. transactions, transfers, logs, NFTs, etc.).

## Cursor Pagination

Cursor pagination works by returning a **cursor token** with each response. You pass that cursor into the next request to fetch the next page.

* **First request:** returns `result` + `cursor`
* **Next request:** send the returned `cursor` to get the next page
* When there are no more results, the cursor will be `null`

Cursor pagination is ideal for long lists because performance stays consistent even at large offsets.

## Cursor Pagination in Moralis

Moralis returns a cursor with list endpoints. Keep calling the endpoint with the latest cursor until no cursor is returned.

**Important notes**

* `limit` can only be set on the **initial request**. You can’t change the limit mid-pagination (because the cursor is tied to the original query settings).
* A cursor represents a **stable snapshot of the dataset at the time your first request was made** (a “point in time”).

## Snapshot Behavior (No Duplicates Across Pages)

When you paginate using a cursor, Moralis keeps the ordering consistent across pages for that pagination session.

Example: if you’re fetching “latest wallet transactions” and **new transactions occur while you’re paging**, those new transactions:

* **will not** reshuffle the pages you’re currently fetching
* **will not** cause items from page 1 to appear again on page 2
* **will not** be included in the current cursor run

If you want **new / delta results**, you should **start a new request** (i.e., re-call the endpoint without the old cursor) after you finish paging, or periodically re-poll from the top depending on your use case.

## Example: Cursor Pagination

Below is a simple Node.js example showing how to page through all results using a cursor.

This example:

* Makes an initial request with a `limit`
* Reuses the returned `cursor` to fetch the next page
* Stops when no cursor is returned
* Uses plain `fetch`

```typescript theme={null}
const fetch = require("node-fetch");

const API_KEY = "YOUR_API_KEY";
const BASE_URL = "https://deep-index.moralis.io/api/v2.2";

const address = "0xb47e3cd837dDF8e4c57F05d70Ab865de6e193BBB";
const chain = "eth";
const limit = 100;

async function fetchAllPages() {
  let cursor = null;
  let allResults = [];

  do {
    const url = new URL(`${BASE_URL}/nft/${address}/owners`);
    url.searchParams.set("chain", chain);
    url.searchParams.set("limit", limit);

    if (cursor) {
      url.searchParams.set("cursor", cursor);
    }

    const res = await fetch(url.toString(), {
      headers: {
        "X-API-Key": API_KEY,
      },
    });

    const data = await res.json();

    allResults.push(...data.result);

    cursor = data.cursor; // null / empty when no more pages
  } while (cursor);

  return allResults;
}

fetchAllPages().then((results) => {
  console.log("Total records:", results.length);
});
```
