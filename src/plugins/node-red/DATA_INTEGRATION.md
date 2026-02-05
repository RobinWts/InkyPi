# Node-RED Data Integration Approache

This document outlines practical ways to receive data from Node-RED flows using built-in nodes (no custom nodes required).

## HTTP In + HTTP Response Nodes

**Best for:** Most use cases - simple, flexible, and uses only built-in Node-RED nodes.

### How It Works

1. **In Node-RED Flow:**
   - Add an **HTTP In** node configured as:
     - Method: `GET`
     - URL: `/inkypi/data` (or any custom path)
   - Add a **Function** node (optional) to format your data:
     ```javascript
     // Format your data here
     msg.payload = {
         temperature: flow.get("temperature") || 0,
         humidity: flow.get("humidity") || 0,
         timestamp: new Date().toISOString()
     };
     return msg;
     ```
   - Add an **HTTP Response** node configured as:
     - Status Code: `200`
     - Headers: `Content-Type: application/json`
   - Wire them together: `HTTP In` → `Function` → `HTTP Response`

2. **In InkyPi Plugin:**
   - Make HTTP GET requests to: `http://[node-red-host]:[port]/inkypi/data`
   - Parse the JSON response
   - Display the data on the e-ink display

### Advantages
- ✅ Uses only built-in Node-RED nodes
- ✅ Simple to set up in Node-RED
- ✅ Flexible - can format data however needed
- ✅ Standard HTTP/JSON - easy to debug
- ✅ Can add authentication via `httpNodeMiddleware` if needed

### Example Node-RED Flow JSON
```json
[
    {
        "id": "http-in-1",
        "type": "http in",
        "z": "flow1",
        "name": "InkyPi Data",
        "url": "/inkypi/data",
        "method": "get",
        "wires": [["function-1"]]
    },
    {
        "id": "function-1",
        "type": "function",
        "z": "flow1",
        "name": "Format Data",
        "func": "msg.payload = {\n    temperature: flow.get('temp') || 0,\n    status: 'active'\n};\nreturn msg;",
        "wires": [["http-response-1"]]
    },
    {
        "id": "http-response-1",
        "type": "http response",
        "z": "flow1",
        "name": "",
        "statusCode": "200",
        "headers": {"Content-Type": "application/json"},
        "wires": []
    }
]
```

## References

- [Node-RED HTTP In Node Documentation](https://nodered.org/docs/user-guide/nodes#http-in)
- [Node-RED HTTP Response Node Documentation](https://nodered.org/docs/user-guide/nodes#http-response)
