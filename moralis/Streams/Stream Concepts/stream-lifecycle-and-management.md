> ## Documentation Index
> Fetch the complete documentation index at: https://docs.moralis.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Stream Lifecycle

> Learn how to manage Streams throughout their lifecycle, including monitoring status, updating configuration, changing regions, and pausing or resuming streams.

## Overview

Moralis Streams can be **created, monitored, updated, paused, and resumed** at any time - either programmatically or via the Moralis dashboard.

This gives you full control over how streams behave in production and allows you to safely manage changes without deleting or recreating streams.

***

## Stream States

Each stream has a lifecycle state that indicates whether it is actively delivering events.

### Supported statuses

| Status       | Description                                                      |
| :----------- | :--------------------------------------------------------------- |
| `active`     | Stream is live and delivering webhooks                           |
| `paused`     | Stream is temporarily disabled                                   |
| `error`      | Stream encountered a configuration or delivery error             |
| `terminated` | Stream was automatically stopped after 24 hours in `error` state |

The current status is returned when listing or fetching streams.

***

## Listing Streams

You can retrieve all streams associated with your account to inspect their configuration and status.

```javascript theme={null}
const streams = await Moralis.Streams.getAll({
  limit: 100,
});
```

Each stream includes metadata such as:

* Webhook URL
* Enabled chains
* Status
* Filters and ABI configuration
* Region and delivery settings

Streams can also be viewed and managed from the dashboard.

***

## Updating Stream Configuration

Streams can be updated at any time to reflect changes such as:

* Webhook URL updates
* Adding or removing chains
* Adjusting filters or ABIs
* Changing stream behavior

Example: updating a webhook URL

```javascript theme={null}
await Moralis.Streams.update({
  id: "STREAM_ID",
  webhook: "https://your-new-webhook-url",
});
```

Updates take effect immediately and do not require stream recreation.

***

## Pausing and Resuming Streams

Streams can be paused without deleting them. This is useful for:

* Maintenance windows
* Incident response
* Temporary traffic reduction

### Pause a stream

```javascript theme={null}
await Moralis.Streams.updateStatus({
  id: "STREAM_ID",
  status: "paused",
});
```

### Resume a stream

```javascript theme={null}
await Moralis.Streams.updateStatus({
  id: "STREAM_ID",
  status: "active",
});
```

Paused streams do not process events and do not send webhooks.

***

## Stream Regions

Each stream runs in a specific region to optimise webhook delivery latency.

Available regions include:

* `us-east-1`
* `us-west-2`
* `eu-central-1`

You can update the region at any time:

```javascript theme={null}
await Moralis.Streams.setSettings({
  region: "eu-central-1",
});
```

For best performance, choose the region closest to your backend infrastructure.

***

## Error Handling

If a stream enters the `error` state:

* The stream stops delivering events
* A status message is provided explaining the issue
* Configuration must be corrected before resuming

Common causes include:

* Invalid ABI definitions
* Invalid filters
* Unreachable webhook endpoints

Read more about [Error Handling](/streams/streams-concepts/error-handling).

***

## Terminated State

If a stream remains in the `error` state for **24 hours**, it is automatically **terminated**.

A terminated stream:

* Does **not** send webhooks
* Does **not** process new blocks
* Drops all events that occur after termination
* Cannot be automatically resumed

When a stream is terminated, an **email notification** is sent to the account owner.

Read more about [Terminated States](/streams/streams-concepts/error-handling).

***

## Best Practices

* Pause streams instead of deleting them when troubleshooting
* Monitor stream status regularly in production
* Keep webhook URLs and regions aligned with your deployment setup
* Use descriptive stream tags to identify purpose and ownership
