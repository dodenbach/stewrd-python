# stewrd

Python SDK for the [Stewrd](https://stewrd.dev) Agent API.

## Install

```bash
pip install stewrd
```

## Quickstart

```python
from stewrd import Stewrd

stewrd = Stewrd("sk-stw_your_key")

result = stewrd.agent.run(
    message="Research the top 5 CRM tools",
    capabilities=["research", "documents"],
)

print(result.message)
print(result.files[0].url)
```

## Streaming

```python
for event in stewrd.agent.stream(message="Write a detailed analysis"):
    if event.type == "token":
        print(event.content, end="")
    if event.type == "tool_start":
        print(f"Using {event.tool}...")
    if event.type == "done":
        print(f"\n\nTokens: {event.usage.tokens_used}")
```

You can also collect the full response after streaming:

```python
stream = stewrd.agent.stream(message="Hello")
response = stream.final_response()
print(response.message)
```

## Configuration

```python
stewrd = Stewrd(
    "sk-stw_...",
    base_url="https://api.stewrd.dev",  # default
    timeout=120.0,                       # default, in seconds
)
```

## API Reference

### `Stewrd(api_key, *, base_url, timeout)`

Create a new client instance.

| Param | Type | Description |
|-------|------|-------------|
| `api_key` | `str` | Your Stewrd API key (`sk-stw_...`) |
| `base_url` | `str` | API base URL (default: `https://api.stewrd.dev`) |
| `timeout` | `float` | Request timeout in seconds (default: `120.0`) |

### `stewrd.agent.run(message, *, capabilities, files)`

Run the agent synchronously. Returns `AgentResponse`.

| Param | Type | Description |
|-------|------|-------------|
| `message` | `str` | The instruction for the agent |
| `capabilities` | `list[str]` | Capabilities to enable (e.g. `["research", "documents"]`) |
| `files` | `list[InputFile]` | Files to include as context |

### `stewrd.agent.stream(message, *, capabilities, files)`

Run the agent with streaming. Returns `AgentStream`.

Takes the same params as `run()`. The returned `AgentStream` is an `Iterator[StreamEvent]`.

### Stream Events

| Event | Fields | Description |
|-------|--------|-------------|
| `token` | `content: str` | A chunk of response text |
| `tool_start` | `tool: str` | A tool invocation started |
| `tool_end` | `tool: str` | A tool invocation finished |
| `done` | `response, usage` | Stream complete with full response |
| `error` | `code: str, message: str` | An error occurred |

### `StewrdError`

Thrown on non-2xx API responses.

```python
from stewrd import Stewrd, StewrdError

try:
    stewrd.agent.run(message="...")
except StewrdError as e:
    print(e.status)   # 401
    print(e.code)     # 'invalid_api_key'
    print(e.message)  # 'Invalid API key'
    print(e.docs)     # 'https://docs.stewrd.dev/errors/invalid_api_key'
```

## Requirements

- Python 3.9+
- [`httpx`](https://www.python-httpx.org/) (installed automatically)

## License

MIT
