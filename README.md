# Walko

<hr/>

A simple CLI application that calculates performance for a given wallet address, such as PnL (profit and loss), win rate ...

## Features
<hr/>
- Performance calculations for a single wallet address
- Top performing wallets lookup to calculate results
- Exporting records (as JSON or .csv)

# Usage
<hr/>

Activate virtual enviroment:

```shell
.\venv\Scripts\activate
```

Running the application:
```shell
python main.py
```

The app uses various APIs to function, such as DexScreener, Solana RPC, Birdeye ...

Most of them are free, but are rate limited. You need to get an API key for Birdeye and place it in `./config`

### Example Birdeye api config file
> Name it: birdeye.json
```json
{
  "api_key": "a405dfeba27945c8b7590e3655c3c0dc"
}
```

# Considerations
<hr/>

- The app is quite barebones. While it supports top address fetching, it is severely rate limited and may hang up.
- Async functionality should be implemented.
- Currently, only the Solana chain is supported, since blockchain APIs are locked down. I would like to expand the functionality to at least the Etherum chain.
- Some addresses like one time traders, insiders, liquidity pools could be filtered out programmatically.


